"""
union_qc.py

Submits a query to get all information from a Synapse table
Validates table entries against a schematic data model
Returns row identifer and validation state
Stores a table in Synapse with id and validation info

author: orion.banks
"""

import synapseclient
import argparse
import pandas as pd
from pathlib import Path
import subprocess
import sys

### Login to Synapse ###
def login():

    syn = synapseclient.Synapse()
    syn.login()

    return syn


def get_args():
	
	parser = argparse.ArgumentParser(
        description='Access and validate tables from Synapse')
	parser.add_argument('-l',
						nargs='+',
                        help='Synapse table IDs to query.')
	parser.add_argument('-c',
                        help='path to schematic config.yml')
	parser.add_argument('-m',
						action='store_true',
                        help='Boolean; if flag is provided, manifest rows will be merged by primary key.')
	return parser.parse_args()


def get_tables(syn, tableIdList, mergeFlag):
	
	tables = [] #set up lists to store info
	names = []
	
	for tableId in tableIdList:
		
		table = syn.tableQuery(f"SELECT * FROM {tableId}").asDataFrame() #pull table from Synapse
		name = table.iat[1,0] #grab name of data type from table; assumes "Component" is first column in table
		
		manifestPath = Path(f"output/{name}.csv") #build path to store table as CSV
		manifestPath.parent.mkdir(parents=True, exist_ok=True) #create folder to store CSVs
		
		table.to_csv(manifestPath, index=False, lineterminator='\n') #convert df to CSV
		
		if mergeFlag:
			tables.append(table) #if merging, store the table for the next function
		else:
			tables.append(manifestPath) #if not merging, store the file path for the next function
		
		names.append(name) #store the name for next functions
	
	return list(zip(tables, names))

def combine_rows(args):
	
	newTables, newNames = zip(*args) #unpack the input

	groups = []
	names = []
	
	for table, name in zip(newTables, newNames):
		table = table.astype(str) #make everything strings so they can be joined as needed

		nameParts = [name, "id"] #define parts of component_id column name

		componentColumn = "Component"
		idColumn = "_".join(nameParts) #build component_id column name

		if name in ["PublicationView", "DatasetView", "ToolView"]:
			#define parts of column names with common formats between manifests
			#build column names
			#access mapping dictionaries associated with manifest types

			grantParts = [name[:-4], "Grant Number"] 
			grantColumn = " ".join(grantParts) 
			
			if name in ["PublicationView", "DatasetView"]:
				assayParts = [name[:-4], "Assay"]
				tumorParts = [name[:-4], "Tumor Type"]
				tissueParts = [name[:-4], "Tissue"]

				assayColumn = " ".join(assayParts)
				tumorColumn = " ".join(tumorParts)
				tissueColumn = " ".join(tissueParts)

				if name == "PublicationView":
			
					aliasColumn = "Pubmed Id" #column to group entries by

					mapping = { #defines how info in each column is handled by row merging function
						componentColumn : "first", 
						idColumn : ",".join, 
						grantColumn : ",".join, 
						"Publication Doi" : "first", 
						"Publication Journal" : "first",
						"Pubmed Url" : "first",
						"Publication Title" : "first",
						"Publication Year" : "first",
						"Publication Keywords" : "first",
						"Publication Authors" : "first",
						"Publication Abstract" : "first",
						assayColumn : "first",
						tumorColumn : "first",
						tissueColumn : "first",
						"Publication Accessibility" : "first",
						"Publication Dataset Alias" : "first",
						"entityId" : ",".join
						}

				elif name == "DatasetView":
			
					aliasColumn = "Dataset Alias"
			
					mapping = {
						componentColumn : "first", 
						idColumn : ",".join, 
						"Dataset Pubmed Id" : "first",
						grantColumn : ",".join, 
						"Dataset Name" : "first",
						"Dataset Description" : "first",
						"Dataset Design" : "first",
						assayColumn : "first",
						"Dataset Species" : "first",
						tumorColumn : "first",
						tissueColumn : "first",
						"Dataset Url" : "first",
						"Dataset File Formats" : "first",
						"entityId" : ",".join
						}
		
			elif name == "ToolView":
			
				aliasColumn = "Tool Name"
			
				mapping = {
					componentColumn : "first", 
					idColumn : ",".join, 
					"Tool Pubmed Id" : "first",
					grantColumn : ",".join,
					"Tool Description" : "first",
					"Tool Homepage" : "first",
					"Tool Version" : "first",
					"Tool Operation" : "first",
					"Tool Input Data" : "first",
					"Tool Output Data" : "first",
					"Tool Input Format" : "first",
					"Tool Output Format" : "first",
					"Tool Function Note" : "first",
					"Tool Cmd" : "first",
					"Tool Type" : "first",
					"Tool Topic" : "first",
					"Tool Operating System" : "first",
					"Tool Language" : "first",
					"Tool License" : "first",
					"Tool Cost" : "first",
					"Tool Accessibility" : "first",
					"Tool Download Url" : "first",
					"Tool Download Type" : "first",
					"Tool Download Note" : "first",
					"Tool Download Version" : "first",
					"Tool Documentation Url" : "first",
					"Tool Documentation Type" : "first",
					"Tool Documentation Note" : "first",
					"Tool Link Url" : "first",
					"Tool Link Type" : "first",
					"Tool Link Note" : "first",
					"entityId" : ",".join
					}

		elif name == "EducationalResource":

			aliasColumn = "Resource Alias"
			
			mapping = {
					componentColumn : "first", 
					idColumn : ",".join, 
					"Resource Title" : "first",
					"Resource Link" : "first", 
					"Resource Topic" : "first",
					"Resource Activity Type" : "first",
					"Resource Primary Format" : "first",
					"Resource Intended Use" : "first",
					"Resource Primary Audience" : "first",
					"Resource Educational Level" : "first",
					"Resource Description" : "first",
					"Resource Origin Institution" : "first",
					"Resource Language" : "first",
					"Resource Contributors" : "first",
					"Resource Grant Number" : ",".join,
					"Resource Secondary Topic" : "first",
					"Resource License" : "first",
					"Resource Use Requirements" : "first",
					"Resource Internal Identifier" : "first",
					"Resource Media Accessibility" : "first",
					"Resource Access Hazard" : "first",
					"Resource Dataset Alias" : "first",
					"Resource Tool Link" : "first",
					"entityId" : ",".join
					}

		mergedTable = table.groupby(aliasColumn, as_index=False).agg(mapping).reset_index() #group rows by designated identifier and map attributes
		mergedTable = mergedTable.iloc[:,1:-1] #remove unnecessary "id" column
		
		mergePath = Path(f"output/{name}_merged.csv")
		mergePath.parent.mkdir(parents=True, exist_ok=True)
		
		mergedTable.to_csv(mergePath, index=False)
		
		groups.append(mergePath)
		names.append(nameParts[0])
		
	return list(zip(groups, names))

def validate_tables(args, config):

	paths, names = zip(*args)

	validNames = []
	validOuts = []
	validPaths = []

	for path, name in zip(paths, names):
		
		command = [ #pass config, datatype, and CSV path(s) to schematic for validation
			"schematic",
        	"model",
			"-c",
			config,
			"validate",
			"-dt",
			name,
			"-mp",
			str(path)]

		print(f"Validating manifest at: {str(path)}...")

		outPath = Path(f"output/{name}_out.txt")
		outPath.parent.mkdir(parents=True, exist_ok=True)

		errPath = Path(f"output/{name}_error.txt")
		errPath.parent.mkdir(parents=True, exist_ok=True)

		commandOut = open(outPath, "w") #store logs from schematic validation
		errOut = open(errPath, "w")
		
		process = subprocess.run(
			command,
			text=True,
			check=True,
			stdout=commandOut,
			stderr=errOut)
		
		validNames.append(name)
		validOuts.append(outPath)
		validPaths.append(path)

	return list(zip(validNames, validOuts, validPaths))

def parse_out(args):

	names, outs, paths = zip(*args)

	parsedNames = []
	parsedOuts = []
	parsedPaths = []
	
	for name, out, path in zip(names, outs, paths):
		
		parsePath = Path(f"output/{name}_out.csv")
		parsePath.parent.mkdir(parents=True, exist_ok=True)
		
		parsed = pd.read_table(out, sep="], ", header=None, engine="python") #load output from schematic validation
		
		parsedOut = parsed.to_csv(parsePath, index=False, sep="\n", header=False, columns=None, quoting=None) #convert log to useable format

		parsedNames.append(name)
		parsedOuts.append(parsePath)
		parsedPaths.append(path)
	
	return list(zip(parsedNames, parsedOuts, parsedPaths))

def upload_tables(args):

	names, outs, paths = zip(*args)
	
	uploadTable = []

	#subset the tables to include features only
	#add column to represent validation/sync status
	#upload to CCKP - Admin using base CSV name and date of upload as label
	
def main():
	
	syn = login()
	
	args = get_args()
	inputList, config, merge = args.l, args.c, args.m 

	print("Accessing requested tables...")
	newTables = get_tables(syn, inputList, merge)
	print("Table(s) downloaded from Synapse and converted to data frames!")
	print("Source table(s) converted to CSV and stored in local output folder!")
	
	if merge:
		print("Merging rows with matching identifier...")
		newTables = combine_rows(newTables)
		print("Matching rows merged!")
		print("Merged table(s) converted to CSV and stored in local output folder!")
		
		print("Validating merged manifest(s)...")
	
	else:
		print("Validating unmerged manifest(s)...")

	checkTables = validate_tables(newTables, config)
	print("Validation logs stored in local output folder!")
	
	print("Converting validation logs to create reference table...")
	
	print(checkTables)
	validEntries = parse_out(checkTables)
	print("Validation logs converted!")

	#storedTables = upload_tables(validEntries)


if __name__ == "__main__":
    main()