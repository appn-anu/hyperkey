#!/usr/bin/env python3

import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# ---------------------------
# Interactive Selection Helpers
# ---------------------------
def select_from_list(items, prompt_label):
    print(f"\n--- Select {prompt_label} ---")
    print("[0] ENTER MANUALLY / TYPE PATH")
    for i, item in enumerate(items, 1):
        print(f"[{i}] {item}")
    
    while True:
        choice = input(f"Enter number (0-{len(items)}): ").strip()
        if choice == "0":
            val = input(f"Type the manual value for {prompt_label}: ").strip()
            return val if val else None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
        print(f"Invalid selection.")

def get_files_by_ext(ext):
    return [f for f in os.listdir('.') if f.lower().endswith(ext) and os.path.isfile(f)]

# ---------------------------
# Math Helpers
# ---------------------------
def find_closest_wavelength(target, columns):
    """Finds the column header string that is numerically closest to the target wavelength."""
    numeric_cols = []
    for col in columns:
        try:
            val = float(col)
            numeric_cols.append((val, col))
        except ValueError:
            continue
    
    if not numeric_cols:
        return None
        
    closest_col = min(numeric_cols, key=lambda x: abs(x[0] - target))
    # Only return if within a reasonable range (10nm)
    if abs(closest_col[0] - target) > 10:
        return None
    return closest_col[1]

# ---------------------------
# Main
# ---------------------------
def main():
    # 1. Selection Phase
    csv_files = get_files_by_ext('.csv')
    input_csv = select_from_list(csv_files, "Input Spectral CSV")
    if not input_csv or not os.path.exists(input_csv): return

    output_csv = "indices_calculated.csv"
    
    # 2. Load Data with Pandas
    print(f"\nLoading {input_csv}...")
    df = pd.read_csv(input_csv)

    # 3. Map Target Wavelengths
    targets = {
        "705": find_closest_wavelength(705.0, df.columns),
        "750": find_closest_wavelength(750.0, df.columns),
        "860": find_closest_wavelength(860.0, df.columns),
        "1610": find_closest_wavelength(1610.0, df.columns),
        "2190": find_closest_wavelength(2190.0, df.columns),
    }

    # Verify column mapping
    for label, col in targets.items():
        if col:
            print(f"  - {label}nm mapped to column: {col}")
        else:
            print(f"  - ERROR: Wavelength near {label}nm not found.")
            return

    # 4. Calculate Indices
    print("\nCalculating Indices...")
    
    def norm_diff(high, low):
        return (df[high] - df[low]) / (df[high] + df[low])

    df['NDVI705'] = norm_diff(targets["750"], targets["705"])
    df['NDMI'] = norm_diff(targets["860"], targets["1610"])
    df['NBR'] = norm_diff(targets["860"], targets["2190"])

    # Save calculated data
    df.to_csv(output_csv, index=False)
    print(f"Full data saved to '{output_csv}'")

    # 5. Generate Heatmaps
    # We want to compare Genotype vs Treatment
    indices_to_plot = ['NDVI705', 'NDMI', 'NBR']
    
    # Check if required columns for heatmap exist
    if 'Genotype' in df.columns and 'Treatment' in df.columns:
        for index_name in indices_to_plot:
            print(f"Generating Heatmap for {index_name}...")
            
            # Aggregate data: Mean index value per Genotype/Treatment combo
            pivot_table = df.pivot_table(
                values=index_name, 
                index='Genotype', 
                columns='Treatment', 
                aggfunc='mean'
            )

            # Plotting
            plt.figure(figsize=(10, 8))
            sns.heatmap(pivot_table, annot=True, cmap='YlGn', fmt=".3f", cbar_kws={'label': index_name})
            plt.title(f'Heatmap of {index_name} by Genotype and Treatment')
            plt.tight_layout()
            
            # Save the plot
            plot_filename = f"heatmap_{index_name}.png"
            plt.savefig(plot_filename)
            print(f"  - Saved: {plot_filename}")
            plt.close()
    else:
        print("\nSkipping Heatmap: 'Genotype' or 'Treatment' columns not found in CSV.")

    print("\nProcess Complete.")

if __name__ == "__main__":
    main()