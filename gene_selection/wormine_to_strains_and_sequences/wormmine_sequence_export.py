#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from intermine.webservice import Service
import pandas as pd
import numpy as np
import os
import io
service = Service("http://intermine.wormbase.org/tools/wormmine/service")
sys.path.insert(0,'/Users/ibarlow/repositories/chopchop')

#sys.path.insert(0, '/Users/ibarlow/Documents/GitHub/pythonScripts/WormMine')

def wormMinetoFASTA(inputfile):
    """ function to generate FASTA.txt file that can be used for protein alignments
    Input:
       .csv file containing the protein sequences downloaded from wormmine
    Output:
        FASTA_sequences.txt """
    
    #read the csv
    inDF = pd.read_csv(inputfile, index_col = False)
    inDF = inDF.drop_duplicates('Gene.CDSs.protein.symbol')

    #generate output file
    outputFile = os.path.join(os.path.dirname(inputfile), 'FASTA_sequences.txt')

    with open(outputFile, 'w') as fid:
        for i,entry in inDF.iterrows():
            fid.write('>')
            fid.write(entry['Gene.CDSs.protein.symbol'])
            fid.write('\n')
            fid.write(entry['Gene.CDSs.protein.sequence.residues'])
            fid.write('\n')
    return


def LoadGeneInfo(inputID, IDtype, outputDF):
    """ starts SQL query to load the gene information
    Input:
        inputID = ID for input
        IDtype = WBID, CEID, or gene_name
    Output:
        outputDF = dataframe of wormmine information"""
    
    query = service.new_query('Gene')
    # The view specifies the output columns
    query.add_view(
        "name",
        "primaryIdentifier",
        "locations.*",
        "chromosome.primaryIdentifier",
        "CDSs.transcripts.sequence.residues",
        "CDSs.transcripts.exons.locations.*",
        "CDSs.protein.sequence.residues",
        "CDSs.protein.sequence.length",
        "CDSs.protein.symbol"
        )
    if IDtype == 'WBID':
        _q= query.where('Gene.primaryIdentifier', '=', inputID).results('dict')
    if IDtype == 'CEID':
        _q = query.wherer('Gene.CDSs.protein.symbol', '=', inputID).results('dict')
    if IDtype == 'gene_name':
        _q = query.wherer('Gene.name', '=', inputID).results('dict')
    for row in _q:
        outputDF = outputDF.append(pd.Series(row), ignore_index=True)
    return outputDF



def WormMineSequenceExport(inputIDs, IDtype, margin, large_deletion, large_deletion_size, outputDir, createFASTA):
    """ Function to find cDNAs from list of WormBaseIDs or protein IDs queries (as csv) and outputs
    cDNA sequences, gDNA sequence, sgRNAsearch.csv (name, chrom, start, end) for chopchop query, and .csv
    with all the WormMine output information
    Input:
    inputIDs - .csv containing list of wormbase or protein ids

    margin - two-element tuple of bp around the gene start to look for sgRNAs - for use in chopchop
    eg. [-50 250] will put 'start' locations 50bp before 1st exon start and 'end' 250bp after 1st exon start

    large_deletion = Bool
    
    large_deltion_size = size of requested deletion if large_deletion is true
    
    outputDir - name of directory into which the output .csvs and sequences should be saved

    createFASTA - boolean. If True then a FASTA.txt file is generated for protein alignments

    Output:
    .ape cDNA sequences
    
    sgInputs.csv - for use in chopchop

    WormMineOutput.csv - query results

    FASTA.txt - text file of protein sequences
    """

    #open csv
    with io.open(inputIDs, 'r',  encoding='utf-8-sig') as fid:
    	 IDs = fid.read().split(',')
    #remove dupliates
    IDs = np.unique(IDs)
    
    print (IDs)

    # TODO is there a way of storing the database locally?
    infoDF = pd.DataFrame()
    for item in IDs:
        print ('Finding ' + item)
        infoDF = LoadGeneInfo(item, IDtype, infoDF)
 
    #to save outputs need to first check if outputdirectory exits
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
        print (outputDir + ' created')
    
    #make a subdirectory for cDNA sequences
    cDNAdir = os.path.join(outputDir, 'cDNAsequences')
    if not os.path.exists(cDNAdir):
        os.makedirs(cDNAdir)

    #group dataframe by wormbaseID and to identify first and last exons and export cDNA sequence as .ape
    startExons = pd.DataFrame()
    grouped=  infoDF.groupby('Gene.primaryIdentifier')

    for i in IDs:
        t = grouped.get_group(i)
        _cut1 = pd.Series()
        _cut1['name'] = t.iloc[0]['Gene.name']
        _cut1['chrom'] = 'chr'+t.iloc[0]['Gene.chromosome.primaryIdentifier']     
        #find if first exon is at beginning or end of locations - this depends on the strand
        if (t['Gene.CDSs.transcripts.exons.locations.strand'] == '1').sum() == t.shape[0]: #sense strand
            _cut1['strand'] = 1
            _cut1['start'] = int(t['Gene.CDSs.transcripts.exons.locations.start'].min()+margin[0])
            _cut1['end'] = int(_cut1['start']+margin[1])
        elif (t['Gene.CDSs.transcripts.exons.locations.strand'] == '-1').sum() == t.shape[0]: #antisense
            _cut1['strand']=-1
            _cut1['start'] = int(t['Gene.CDSs.transcripts.exons.locations.end'].max()-margin[0])
            _cut1['end'] = int(_cut1['start']-margin[1])
        startExons = startExons.append(_cut1.to_frame().transpose(), sort=True)
        
        if large_deletion:
            if _cut1['strand']==1:
                _cut2 = pd.Series({'name':_cut1['name']+'_cut2',
                                   'chrom':_cut1['chrom'],
                                   'start':_cut1['start']+large_deletion_size,
                                   'end':_cut1['end']+large_deletion_size,
                                   'strand': _cut1['strand']})
            if _cut1['strand'] == -1:
                _cut2 = pd.Series({'name':_cut1['name']+'_cut2',
                                   'chrom':_cut1['chrom'],
                                   'start':_cut1['start']-large_deletion_size,
                                   'end':_cut1['end']-large_deletion_size,
                                   'strand':_cut1['strand']})
            startExons = startExons.append(_cut2.to_frame().transpose(),sort=True)
        
        #save cDNA sequence
        with open(os.path.join(cDNAdir, _cut1['name'] + '_cDNA.ape'), 'w+') as fopen:
            fopen.write(t.iloc[0]['Gene.CDSs.transcripts.sequence.residues'])
            print (_cut1['name'] + ' cDNA sequence saved')
        del _cut1, _cut2
    
    #save sgRNA input csv from startExons
    startExons.to_csv(os.path.join(outputDir, 'sgInputs.csv'), index=False)
    
    # save WormMine output to csv
    infoDF.to_csv(os.path.join(outputDir, 'WormMineoutput.csv'), index=False)

    #now run twoBittoFa to download the gDNAsequences
    #create subdirectory
    gDNAdir = os.path.join(outputDir, 'gDNAsequences')
    if not os.path.exists(gDNAdir):
        os.makedirs(gDNAdir)
 
    #drop duplicates for saving gDNA
    infoDF = infoDF.drop_duplicates('Gene.symbol')

    for i,r in infoDF.iterrows():
        start = r['Gene.locations.start']
        end = r['Gene.locations.end']
        cmd = './twoBitToFa http://hgdownload.cse.ucsc.edu/gbdb/ce11/ce11.2bit ' + \
        os.path.join(gDNAdir, r['Gene.name'] + '_gDNA.fa')
        cmd += ' -seq=chr'+ r['Gene.chromosome.primaryIdentifier']
        cmd += ' -start=' + str(int(start))
        cmd += ' -end=' + str(int(end))
        print (cmd)

        os.system (cmd)

    if createFASTA:
        wormMinetoFASTA(os.path.join(outputDir, 'WormMineoutput.csv'))
    else:
        print('no FASTA.txt file generated')
    return


if __name__ == '__main__':
    inputIDs = sys.argv[1]
    IDtype = sys.argv[2]
    margin = (int(sys.argv[3]), int(sys.argv[4]))
    large_deletion = sys.argv[5]
    large_deletion_size = int(sys.argv[6])
    outputDir = sys.argv[7]
    createFASTA = sys.argv[8]
    WormMineSequenceExport(inputIDs,
                           IDtype,
                           margin,
                           large_deletion,
                           large_deletion_size,
                           outputDir,
                           createFASTA)