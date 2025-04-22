# time4TI

A simple timer to use when performing temporal interference stimulation experiments. Just built it so that it's a bit easier to keep track of cycles, amplitude and carrier frequencies in one place. 

See:

https://simnibs.github.io/simnibs/build/html/tutorial/tes_flex_opt.html#tes-flex-opt

for a guide on how to find reasonable stimulation coordinates for classic TI (4 electrodes) using a subject T1 MRI. 


See the notebook "Find_closest_electrodes.ipynb" above for a simple way to use the output from SimNIBS in order to find the closest EEG-electrodes to the optimised coordinates using MNE-Python.


Special thanks to Jan Trajlinek! 

See reference below for information on stimulation parameters: 

Missey, F., Acerbo, E., Dickey, A. S., Trajlinek, J., Studnička, O., Lubrano, C., de Araújo e Silva, M., Brady, E., Všianský, V., Szabo, J., Dolezalova, I., Fabo, D., Pail, M., Gutekunst, C.-A., Migliore, R., Migliore, M., Lagarde, S., Carron, R., Karimi, F., … Williamson, A. (2024). Non-invasive Temporal Interference Stimulation of the Hippocampus Suppresses Epileptic Biomarkers in Patients with Epilepsy: Biophysical Differences between Kilohertz and Amplitude Modulated Stimulation. https://doi.org/10.1101/2024.12.05.24303799