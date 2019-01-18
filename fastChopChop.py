#!/usr/bin/env python2.7

""" function to open up a .csv file with genes and genomic_coordinates
and run the chopchop.py query to generate sgRNAs and primers"""

import pandas as pd
import sys
import os

def fastChopChop(input_coords, extra_inputs):
	"""Input:
	input_coords - .csv generated from sgDesignInput.py, which has a columns
	name, chrom, start, end 

	Output:
	sgRNAs and primers for input coordinates as generated by chopchop software"""

	inputDF = pd.read_csv(input_coords)

	outputDir = os.path.join(os.path.dirname(input_coords), 'ChopChop_output')
	if not os.path.exists(outputDir):
		os.makedirs(outputDir)

	for i,r in inputDF.iterrows():
		if r.start>r.end:
			end = str(r.start)
			start = str(r.end)
		else:
			start = str(r.start)
			end = str(r.end)

		cmd = './chopchop.py -G ce11 -o ' + os.path.join(outputDir,r['name']) 
		cmd+= ' ' + r.chrom + ':' + start + '-' + end + ' '
		if extra_inputs >0:
			for item in extra_inputs:
				cmd+= item + ' '
		print(cmd)
		os.system(cmd)

if __name__ == '__main__':
	input_coords = sys.argv[1]
	extra_inputs = sys.argv[2:]
	fastChopChop(input_coords, extra_inputs)
