import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from tkinter import Tk
from tkinter.filedialog import askopenfilename

def plot_violin_and_error(threshold=50):
    # Hide the root window of tkinter
    Tk().withdraw()
    
    # Open file dialog to select the CSV file
    csv_file_path = askopenfilename(
        filetypes=[("CSV files", "*.csv")],
        title="Select CSV File"
    )
    
    if not csv_file_path:
        print("No file selected.")
        return

    # Load the CSV file
    df = pd.read_csv(csv_file_path)

    # Drop NaNs for each column to handle different lengths
    cleaned_df = {col: df[col].dropna() for col in df.columns}
    
    # Create a new DataFrame
    cleaned_df = pd.DataFrame(dict([(k, pd.Series(v.values)) for k, v in cleaned_df.items()]))

    # Melt the DataFrame for use in seaborn
    melted_df = cleaned_df.melt(var_name='Variable', value_name='Value')

    # Check the lengths of each column to determine color
    column_lengths = cleaned_df.apply(lambda x: x.dropna().size)

    # Create the first plot: Violin Plot
    plt.figure(figsize=(10, 6))
    for col in cleaned_df.columns:
        length = column_lengths[col]
        color = 'red' if length < threshold else 'blue'
        
        # Filter the melted DataFrame for each column
        sns.violinplot(
            x='Variable', 
            y='Value', 
            data=melted_df[melted_df['Variable'] == col], 
            color=color
        )
    
    plt.xticks(rotation=45)
    plt.title(f'Violin Plot of CSV Data (Columns with < {threshold} items in red)')
    
    # Calculate the average and standard error of the mean (SEM) for each column
    means = cleaned_df.mean()
    sems = cleaned_df.sem()  # SEM = std / sqrt(n)

    # Define X values as 1, 3, 5, 7, ...
    x_values = np.arange(1, len(means) * 2, 2)

    # Create the second plot: XY Error Plot with SEM
    plt.figure(figsize=(10, 6))
    plt.errorbar(x_values, means, yerr=sems, fmt='o', ecolor='black', capsize=5, label='Mean ± SEM')
    plt.xlabel('X (1, 3, 5, ...)')
    plt.ylabel('Y (Mean of columns)')
    plt.title('XY Error Plot: Mean ± SEM of Each Column')
    plt.xticks(x_values, cleaned_df.columns, rotation=45)
    plt.grid(True)
    plt.legend()
    plt.show()

# Execute the function to select the file and plot the data
plot_violin_and_error(threshold=50)
