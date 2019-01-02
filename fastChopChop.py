#!/usr/bin/env python2.7

""" function to open up a .csv file with genes and genomic_coordinates
and run the chopchop.py query to generate sgRNAs and primers"""

import pandas as pd
import sys
import os

def fastChopChop(input_coords):
	"""Input:
	input_coords - .csv generated from sgDesignInput.py, which has a columns
	name, chrom, start, end 

	Output:
	sgRNAs and primers for input coordinates as generated by chopchop software"""

	inputDF = pd.read_csv(input_coords)

	for i,r in inputDF.iterrows():
		if r.start>r.end:
			end = str(r.start)
			start = str(r.end)
		else:
			start = str(r.start)
			end = str(r.end)

		cmd = './chopchop.py -G ce11 -P -o ' + os.path.join(os.path.dirname(input_coords),r['name']) 
		cmd+= ' ' + r.chrom + ':' + start + '-' + end
		print(cmd)
		os.system(cmd)

if __name__ == '__main__':
	input_coords = sys.argv[1]
	fastChopChop(input_coords)
