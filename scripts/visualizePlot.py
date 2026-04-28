# #!/usr/bin/env python3

# import os
# import pandas as pd
# import seaborn as sns
# import matplotlib.pyplot as plt

# # ---------------------------
# # Helpers
# # ---------------------------
# def find_closest_wavelength(target, columns):
#     numeric_cols = []
#     for col in columns:
#         try:
#             val = float(col)
#             numeric_cols.append((val, col))
#         except ValueError:
#             continue
#     if not numeric_cols: return None
#     closest_col = min(numeric_cols, key=lambda x: abs(x[0] - target))
#     return closest_col[1] if abs(closest_col[0] - target) <= 10 else None

# # ---------------------------
# # Main
# # ---------------------------
# def main():
#     # 1. Selection (Using standard input for simplicity)
#     files = [f for f in os.listdir('.') if f.endswith('.csv')]
#     if not files:
#         print("No CSV files found.")
#         return
    
#     print("\n--- Available Files ---")
#     for i, f in enumerate(files, 1):
#         print(f"[{i}] {f}")
    
#     choice = int(input(f"Select file (1-{len(files)}): "))
#     input_csv = files[choice-1]

#     # 2. Load and Calculate
#     df = pd.read_csv(input_csv)
    
#     targets = {
#         "705": find_closest_wavelength(705.0, df.columns),
#         "750": find_closest_wavelength(750.0, df.columns),
#         "860": find_closest_wavelength(860.0, df.columns),
#         "1610": find_closest_wavelength(1610.0, df.columns),
#         "2190": find_closest_wavelength(2190.0, df.columns),
#     }

#     print("Calculating indices...")
#     df['NDVI705'] = (df[targets["750"]] - df[targets["705"]]) / (df[targets["750"]] + df[targets["705"]])
#     df['NDMI'] = (df[targets["860"]] - df[targets["1610"]]) / (df[targets["860"]] + df[targets["1610"]])
#     df['NBR'] = (df[targets["860"]] - df[targets["2190"]]) / (df[targets["860"]] + df[targets["2190"]])

#     # 3. Unique Row ID (Ensures individual plotting)
#     # We combine Variety and FileNum to see every single measurement separately
#     df['Sample_ID'] = df['Variety'].astype(str) + " (File " + df['FileNum'].astype(str) + ")"

#     indices = ['NDVI705', 'NDMI', 'NBR']
    
#     for idx in indices:
#         print(f"\nDisplaying {idx} Heatmap... (Close window to see next)")
        
#         # Create a pivot table for the heatmap
#         # Index = Samples, Columns = Treatments
#         plot_data = df.pivot(index='Sample_ID', columns='Treatment', values=idx)
        
#         plt.figure(figsize=(10, 8))
#         sns.heatmap(plot_data, 
#                     annot=True, 
#                     cmap='RdYlGn', 
#                     fmt=".3f", 
#                     linewidths=0.5,
#                     cbar_kws={'label': f'Index Value ({idx})'})
        
#         plt.title(f'Individual Measurements: {idx}')
#         plt.xlabel('Treatment Condition')
#         plt.ylabel('Variety & File Number')
#         plt.tight_layout()
        
#         # THIS DISPLAYS THE PLOT
#         plt.show() 

# if __name__ == "__main__":
#     main()

# #Saving the plots as images can be done by replacing `plt.show()` with `plt.savefig(f"{idx}_heatmap.png")` and then calling `plt.close()` to free up memory before the next plot.

#!/usr/bin/env python3

import os
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
    numeric_cols = []
    for col in columns:
        try:
            val = float(col)
            numeric_cols.append((val, col))
        except ValueError:
            continue
    if not numeric_cols: return None
    closest_col = min(numeric_cols, key=lambda x: abs(x[0] - target))
    return closest_col[1] if abs(closest_col[0] - target) <= 10 else None

# ---------------------------
# Main
# ---------------------------
def main():
    # 1. Selection
    csv_files = get_files_by_ext('.csv')
    input_csv = select_from_list(csv_files, "Input Spectral CSV")
    if not input_csv or not os.path.exists(input_csv): return

    # 2. Load Data
    print(f"\nLoading {input_csv}...")
    df = pd.read_csv(input_csv)

    # 3. Map Wavelengths
    targets = {
        "705": find_closest_wavelength(705.0, df.columns),
        "750": find_closest_wavelength(750.0, df.columns),
        "860": find_closest_wavelength(860.0, df.columns),
        "1610": find_closest_wavelength(1610.0, df.columns),
        "2190": find_closest_wavelength(2190.0, df.columns),
    }

    # 4. Calculate Indices
    print("Calculating NDVI705, NDMI, and NBR...")
    df['NDVI705'] = (df[targets["750"]] - df[targets["705"]]) / (df[targets["750"]] + df[targets["705"]])
    df['NDMI'] = (df[targets["860"]] - df[targets["1610"]]) / (df[targets["860"]] + df[targets["1610"]])
    df['NBR'] = (df[targets["860"]] - df[targets["2190"]]) / (df[targets["860"]] + df[targets["2190"]])

    # 5. Create Individual Identifiers
    # We combine Genotype and FileNum to ensure every single measurement is unique
    df['Measurement_Label'] = df['Genotype'].astype(str) + "_" + df['FileNum'].astype(str)

    # 6. Generate Heatmaps
    indices_to_plot = ['NDVI705', 'NDMI', 'NBR']
    
    if 'Treatment' in df.columns:
        for index_name in indices_to_plot:
            print(f"Plotting individual measurements for {index_name}...")
            
            # Pivot without aggregation (using our unique Measurement_Label)
            pivot_table = df.pivot(
                index='Measurement_Label', 
                columns='Treatment', 
                values=index_name
            )

            # Sort the index so genotypes are grouped together visually
            pivot_table = pivot_table.sort_index()

            plt.figure(figsize=(12, 10))
            sns.heatmap(pivot_table, annot=True, cmap='RdYlGn', fmt=".3f", linewidths=.5)
            plt.title(f'Individual Measurements: {index_name}')
            plt.ylabel('Genotype & File Number')
            plt.xlabel('Treatment')
            plt.tight_layout()
            
            plt.savefig(f"individual_heatmap_{index_name}.png")
            plt.close()
            print(f"  - Saved: individual_heatmap_{index_name}.png")
    else:
        print("Error: 'Treatment' column not found. Cannot plot heatmap columns.")

    print("\nProcess Complete. Each measurement is now represented as its own row.")

if __name__ == "__main__":
    main()