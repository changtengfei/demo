"""
Lydia Lee, 2019
This file contains the code specific to the ADC for writing, reading, plotting,
and performing various calculations on ADC data. It does not contain any code to 
actually run tests on the ADC. For that, see adc_*.py. This is 
strictly for information post-processing.
"""
import csv
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

def write_adc_data(adc_outs, file_out):
	"""
	Inputs:
		adc_outs: A dictionary of ADC codes where the key is the vin,
			and the value is a list of measured codes (more than one
			measurement can be taken).
		file_out: String. Path to the file to hold the data.
	Outputs:
		No return value. The first column of the output file is 
		the vin values. The second column is the first of all the 
		iterations of the ADC codes measured for that vin.

		vin1 code_1_1 code_1_2 ...
		vin2 code_2_1 code_2_2 ...
		vin3 code_3_1 code_3_2 ...
	"""
	with open(file_out, 'w') as f:
		fwriter = csv.writer(f)
		for vin in adc_outs.keys():
			row = [vin] + adc_outs[vin]
			fwriter.writerow(row)
	return

def read_adc_data(file_in):
	"""
	Inputs:
		file_in: String. Path to the file containing the data. The format
			should have it that the first column is the vin values, and all
			subsequent columns are the ADC output codes for the vin of the
			same row.

			vin1 code_1_1 code_1_2 ...
			vin2 code_2_1 code_2_2 ...
			vin3 code_3_1 code_3_2 ...
	Outputs:
		Returns a dictionary of ADC codes where the key is the vin
			and the value is a list of measured codes.
	Raises:
		ValueError if anything in the input file can't be cast 
		to a float.
	"""
	adc_outs = dict()
	with open(file_in, 'r') as f:
		freader = csv.reader(f)
		for row in freader:
			# Sometimes the thing reads empty rows where there are none
			if len(row) == 0:
				continue
			# Casting call, anyone?
			vin = float(row[0])
			codes = [float(i.replace("b'", '').replace("\n'",'')) for i in row[1:]]
			adc_outs[vin] = codes
	return adc_outs

def calc_adc_dnl_endpoint(adc_outs):
	"""
	Inputs: 
		adc_outs: A dictionary of ADC codes where the key is the vin,
			and the value is a list of measured codes (more than one
			measurement can be taken).
	Outputs:
		Returns a collection of endpoint DNLs for each nominal LSB.
	"""
	all_codes = []
	for vin,code_list in adc_outs.items():
		all_codes = all_codes + list([int(x) for x in code_list])

	all_codes = set(all_codes)

	data_hist = [0]*(max(all_codes)+1)
	for vin,code_list in adc_outs.items():
		for code in code_list:
			data_hist[int(code)] = data_hist[int(code)] + 1

	Wavg = np.average(data_hist[1:len(data_hist)-1])
	DNL = [W/Wavg-1 for W in data_hist]

	DNL[0] = float('nan')
	DNL[-1] = float('nan')

	return DNL

def calc_adc_inl_endpoint(adc_outs):
	"""
	Inputs: 
		adc_outs: A dictionary of ADC codes where the key is the vin,
			and the value is a list of measured codes (more than one
			measurement can be taken).
	Outputs:
		Returns a collection of endpoint INLs taken from the minimum
		input voltage up to the maximum input voltage.
	"""
	DNL = calc_adc_dnl_endpoint(adc_outs)
	INL = [float('nan')] + [sum(DNL[1:i]) for i in range(1, len(DNL))]
	# INL_cleaned = [x for x in INL if not np.isnan(x)]

	return INL

def calc_adc_inl_straightline(adc_outs, vlsb_ideal):
	"""
	Inputs: 
		adc_outs: A dictionary of ADC codes where the key is the vin,
			and the value is a list of measured codes (more than one
			measurement can be taken).
		vlsb_ideal: The nominal voltage associated with a single LSB.
	Outputs:
		Returns the slope, intercept of the linear regression of the 
		ADC codes vs. vin.
	"""
	# Averaging over all the iterations to get an average of what the ADC
	# returns.
	adc_outs_avg = {vin:round(np.average(codes)) for (vin,codes) \
					in adc_outs.items()}

	# Using linear regressiontto figure out the slope and intercept
	x = list(adc_outs_avg.keys())
	y = [adc_outs_avg[k] for k in x]
	slope, intercept, r_value, p_value, std_error = stats.linregress(x, y)

	return slope, intercept




def plot_adc_data(adc_outs, plot_inl=False, plot_ideal=False, vdd=1.2, num_bits=10):
	"""
	Inputs: 
		adc_outs: A dictionary of ADC codes where the key is the vin,
			and the value is a list of measured integer codes (more than one
			measurement can be taken).
		plot_inl: Boolean. If true, plot the INL over the same plot. If false,
			don't plot the linear approximation.
		plot_ideal: Boolean. If true, plot the ``ideal'' ADC output in the same
			plot. If false, don't bother.
		vdd: Float. Full scale range (in volts) of the ADC input.
		num_bits: Integer. Nominal number of bits for the ADC.
	Outputs:
		No return value. Plots the average of the ADC code vs. vin. May also plot the
		INL approximation and the 
	Raises:
		ValueError if not all of the values of Vin have the same number of iterations
		associated with them, e.g. Vin=1V was read for 3 cycles, but Vin=1.1V was read 
		for 10.
	"""
	num_iterations_set = set([len(codes) for (vin,codes) in adc_outs.items()])
	if len(num_iterations_set) != 1:
		raise ValueError("Variable number of iterations for each Vin value.")

	num_iterations = num_iterations_set.pop()
	adc_avg = {vin:round(np.average(codes)) for (vin,codes) \
					in adc_outs.items()}
	vlsb_ideal=vdd/2**num_bits

	x = list(adc_avg.keys())
	y = [adc_avg[i] for i in x]
	plt.plot(x,y,label="ADC Codes")

	title_str = "$V_{DD}$"
	title_str = title_str + " = {} V\nAverage Over {} Samples".format(vdd, num_iterations)

	if plot_inl:
		slope, intercept = calc_adc_inl_straightline(adc_outs, vlsb_ideal)
		plt.plot(x,[slope*i+intercept for i in x],label="INL")
		title_str = title_str + "\nINL Slope: {} codes/V\nINL Y-Intercept: {} codes".format(slope, intercept)

	if plot_ideal:
		plt.plot(x,[1/vlsb_ideal*i for i in x],label="Ideal")
	
	if plot_ideal or plot_inl:
		plt.legend()

	plt.xlabel("$V_{IN}$ (V)")
	plt.ylabel("ADC Code")
	plt.grid()
	plt.title(title_str)
	plt.show()

if __name__ == "__main__":
	### Testing write ###
	if False:
		adc_outs = {i/2:[j*i for j in range(5)] for i in range(3)}
		print(adc_outs)
		write_adc_data(adc_outs, './test_write.csv')

	### Testing write and read ###
	if False:
		fname = './test_write.csv'
		adc_outs = {i/2:[float(j*i) for j in range(5)] for i in range(3)}
		write_adc_data(adc_outs, fname)
		reread_adc_outs = read_adc_data(fname)
		print(adc_outs)
		print(reread_adc_outs)
		print(adc_outs == reread_adc_outs)