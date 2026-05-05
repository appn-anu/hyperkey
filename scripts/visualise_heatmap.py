"""
Heatmap Visualisation Script
Reads hyperspectral data from merged_spectral_data.csv and creates a heatmap of NDVI values
arranged in a grid as close to square as possible.
"""

import load_data as ld
import numpy as np
import matplotlib.pyplot as plt


def find_closest_wavelength(wavelengths, target):
    """Find the wavelength closest to the target value."""
    wavelengths = wavelengths.astype(float)
    idx = np.abs(wavelengths - target).argmin()
    return idx, wavelengths[idx]


def calculate_ndvi(df):
    """
    Calculate NDVI for each measurement.
    NDVI = (NIR - Red) / (NIR + Red)
    Using typical Red (~670nm) and NIR (~800nm) bands.
    """
    # Get wavelengths from column names
    wavelengths = df.columns.astype(float)
    
    # Find closest wavelengths to Red and NIR bands
    red_idx, red_wavelength = find_closest_wavelength(wavelengths, 670)
    nir_idx, nir_wavelength = find_closest_wavelength(wavelengths, 800)
    
    print(f"Using Red band: {red_wavelength:.1f}nm (index {red_idx})")
    print(f"Using NIR band: {nir_wavelength:.1f}nm (index {nir_idx})")
    
    # Extract Red and NIR reflectance values
    red = df.iloc[:, red_idx].values
    nir = df.iloc[:, nir_idx].values
    
    # Calculate NDVI
    ndvi = (nir - red) / (nir + red)
    
    return ndvi


def calculate_square_grid(n_measurements):
    """
    Calculate the best square-ish grid dimensions for the heatmap.
    Returns (rows, cols) where rows * cols >= n_measurements and is as close to square as possible.
    """
    # Start with the square root
    side = int(np.ceil(np.sqrt(n_measurements)))
    
    # Try to make it as square as possible
    # First try: rows = side, cols = side (might have extra cells)
    # If that's too wide, try: rows = side, cols = side - 1
    
    best_rows = side
    best_cols = side
    
    # Calculate the difference from square
    diff = (best_rows * best_cols) - n_measurements
    
    # Try decreasing columns if that gives a better fit
    if side > 1:
        diff_alt = (side * (side - 1)) - n_measurements
        if 0 <= diff_alt < diff:
            best_cols = side - 1
    
    return best_rows, best_cols


def create_heatmap(visual_type, visual_values, measurement_names, output_path=None):
    """
    Create a heatmap of specified values in a square-ish grid.
    """
    n_measurements = len(visual_values)
    
    # Calculate optimal grid dimensions
    rows, cols = calculate_square_grid(n_measurements)
    print(f"\nGrid dimensions: {rows} x {cols} = {rows * cols} cells for {n_measurements} measurements")
    
    # Create grid (pad with NaN if needed)
    grid = np.full(rows * cols, np.nan)
    grid[:n_measurements] = visual_values
    grid = grid.reshape(rows, cols)
    
    # Create the heatmap
    _, ax = plt.subplots(figsize=(10, 8))
    
    # Create heatmap with a good colormap for NDVI
    # NDVI ranges from -1 to 1, so we use a diverging colormap
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-1, vmax=1, aspect='equal')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, label=visual_type)
    cbar.ax.tick_params(labelsize=10)
    
    # Set labels
    ax.set_title(f'{visual_type} Heatmap ({rows}x{cols} grid)', fontsize=14, fontweight='bold')
    
    # Remove axis ticks and labels for clean grid look
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    
    # Add measurement names as text in each cell
    for i in range(rows):
        for j in range(cols):
            cell_idx = i * cols + j
            if cell_idx < n_measurements:
                # Get short name from measurement
                name = measurement_names[cell_idx]
                # Extract just the number part for display
                short_name = name.replace('HR.032426.', '').replace('.sig', '')
                text_color = 'white' if grid[i, j] < 0 or grid[i, j] > 0.7 else 'black'
                ax.text(j, i, short_name, ha='center', va='center', 
                       fontsize=8, color=text_color, fontweight='bold')
    
    plt.tight_layout()
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Heatmap saved to: {output_path}")
    else:
        plt.show()
    
    plt.close()
    
    return grid


def main():
    # Get project root and use relative paths
    project_root = ld.get_project_root()
    input_csv = project_root / 'data' / 'output_data' / 'merged_spectral_data.csv'
    output_image = project_root / 'data' / 'output_data' / 'ndvi_heatmap.png'
    
    print("Loading spectral data...")
    df = ld.load_spectral_data(input_csv)
    print(f"Loaded {len(df)} measurements with {len(df.columns)} wavelength bands")
    
    print("\nCalculating NDVI...")
    ndvi_values = calculate_ndvi(df)
    
    # Print summary statistics
    print(f"\nStatistics:")
    print(f"  Min: {np.nanmin(ndvi_values):.4f}")
    print(f"  Max: {np.nanmax(ndvi_values):.4f}")
    print(f"  Mean: {np.nanmean(ndvi_values):.4f}")
    print(f"  Std: {np.nanstd(ndvi_values):.4f}")
    
    # Create heatmap
    print("\nCreating heatmap...")
    create_heatmap("NDVI", ndvi_values, df.index.tolist(), output_image)
    
    print("\nDone!")


if __name__ == '__main__':
    main()