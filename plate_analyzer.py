import sys, os, argparse
import xml.etree.ElementTree as ET
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from rstoolbox.plot import plot_96wells

################################
#   User Defined Parameters    #
################################

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--directory', help='[Required]	Path to directory where plate reader files are stored.', required=True)
parser.add_argument('-n', '--number_of_wave_lengths', help='[Not required]	Number of wave lengths analysed per file. (Default = 1)', required=False)
parser.add_argument('-o', '--output', help='[Not required]	Output directory. (Default = same as input directory).', required=False)
parser.add_argument('-c', '--cutoff', help='[Not required]	Cut-off difference in absorbance to include in line plot. (Default = 0.2)', required=False)
args = parser.parse_args()

################################
#    Initial Configuration     #
################################

file_path = args.directory
files = os.listdir(file_path)

if args.output:
	os.system("mkdir -p "+args.output)
else:
	out_dir = args.directory

if args.cutoff:
	cutoff = float(args.cutoff)
else:
	cutoff = 0.2
if args.number_of_wave_lengths:
	wave_lengths_n = args.number_of_wave_lengths
else:
	wave_lengths_n = 1

################################
#   Parse Plate Reader Files   #
################################

def parse_plate_files(files):
	df_list, days_list, wave_lengths_list = [], [], []
	letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
	numbers = list(range(1, 13))
	# List with row numbers where each data is stored for each wave length
	row_n_wave_length_reads = [[0, 52, 62],
			[1, 62, 72],
			[2, 72, 82],
			[3, 82, 92],
			[4, 92, 102],
			[5, 102, 112]]

	for filename in files:
		if ".xml" in filename:
			# Get the day number from the file name
			day = int(filename.split("_")[1].split("D")[0])
			days_list.append(day)

			# Parses the .xml file using the ET library
			tree = ET.parse(file_path+filename)
			root = tree.getroot()

			plate = []
			
			# Creates an empty list of lists the size of the whole file, with one list per line and one item per cell
			for row in root[3][0]:
				for collumn in row:
					plate.append([])

			# Loops through the .xml file and appends each cell to the plate list
			for row in root[3][0]:
				for collumn in row:
					for cell in collumn:
							row_n = int(row.attrib["{urn:schemas-microsoft-com:office:spreadsheet}Index"])-1
							collumn_n = int(collumn.attrib["{urn:schemas-microsoft-com:office:spreadsheet}Index"])-1
							plate[row_n].append(cell.text)
			
			
			# Loops through the list with wave lengths and positions and create df_list
			for item in row_n_wave_length_reads:
				wave_length_n = item[0]
				first_row = item[1]
				last_row = item[2]
				new_plate = plate[first_row:last_row]
				wave_length = new_plate[1][1].split(" ")[0]
				wave_lengths_list.append(wave_length)
				i = 0
				for row in new_plate[2:]:
					j = 0
					for collumn in row[1:]:
						cell = letters[i]+str(numbers[j])
						if collumn == "#SAT":
							collumn = 4.000
						df_list.append([day, wave_length, cell, collumn])
						j += 1
					i += 1
	days_list.sort()
	wave_lengths_list = list(set(wave_lengths_list))
	wave_lengths_list.sort()

	return(df_list, days_list, wave_lengths_list)

################################
#       Generate Plots         #
################################

def generate_line_plots(df_list, wave_lengths_list):
	df = pd.DataFrame(df_list)
	df[3] = df[3].astype(float)
	df.columns = ['Days', "Wave_length", "Well","Absorbance"]

	for wave_length in wave_lengths_list:
		new_df = df[df["Wave_length"] == wave_length]
		new_df["Delta"] = ""
		well_dict = {}
		for index, row in new_df.iterrows():
			if row["Well"] not in well_dict:
				well_dict[row["Well"]] = [row["Absorbance"]]
			else:
				well_dict[row["Well"]].append(row["Absorbance"])
		for key, value in well_dict.items():
			min_abs = min(value)
			max_abs = max(value)
			delta = max_abs-min_abs
			for index, row in new_df.iterrows():
				if row["Well"] == key:
					new_df.at[index, 'Delta'] = delta
					new_df.at[index, 'Well'] = key+" "+str(delta)[:5]
		
		new_df = new_df[new_df["Delta"] >= cutoff]
		print(new_df)
		fig, ax = plt.subplots(figsize=(16, 10))
		# Create plot using seaborn, extra funcionts can be found at: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.plot.html
		line_plot = sns.lineplot(ax = ax, data=new_df, x="Days", y="Absorbance", hue="Well", style = "Well", markers=True, dashes = False, lw=3, markersize=14)
		plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)
		figure = line_plot.get_figure()       
		figure.savefig(file_path+"Line_plot_"+wave_length+".png", dpi=400)

	return

def generate_plate_plots(df_list, wave_lengths_list, days_list):
	df = pd.DataFrame(df_list)
	df[3] = df[3].astype(float)
	df.columns = ['Days', "Wave_length", "Well","Absorbance"]

	for day in days_list:
		for wave_length in wave_lengths_list:
			new_list = [[],[],[],[],[],[],[],[]]
			new_df = df[df["Wave_length"] == wave_length]
			new_df = new_df[new_df["Days"] == day]
			i, j = 0, 0
			for index, row in new_df.iterrows():
				new_list[j].append(row['Absorbance'])
				i += 1
				if i == 12:
					i = 0
					j += 1
			df = pd.DataFrame(new_list)
			print(df)
			heatmap = sns.heatmap(df)
			# fig, ax = plot_96wells(cdata = df, sdata = -df, bdata = df<0)
			# plt.subplots_adjust(left=0.1, right=0.8, top=0.9, bottom=0.1)
			# fig.savefig(file_path+"plate_plot_"+day+"_day_"+wave_length+".png", dpi=300)
			# fig, ax = plt.subplots(figsize=(10, 10))
			# line_plot = sns.lineplot(ax = ax, data=new_df, x="Days", y="Absorbance", hue="Well", markers=True)
			# plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)
			figure = heatmap.get_figure()    
			figure.savefig(file_path+"Heatmap_"+wave_length+".png", dpi=400)


	return

################################
#      Run All Functions       #
################################

# Generate lists with the data
df_list, days_list, wave_lengths_list = parse_plate_files(files)

# Plot line plots
generate_line_plots(df_list, wave_lengths_list)

# # Plot plate plots
# generate_plate_plots(df_list, wave_lengths_list, days_list)