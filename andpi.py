import numpy as np
from scipy.signal import find_peaks

from utils import show_heatmap, calculate_frequency_histogram_2d


def calculate_NDPI(input_data):
    """
    Compute the NDPI heatmap for Sentinel-2 MSI
    """
    B11_data = input_data[:, :, -2]
    mix_slice_data = np.zeros((input_data.shape[0], input_data.shape[1], 5))
    mix_slice_data[:, :, 0] = input_data[:, :, 1]
    mix_slice_data[:, :, 1] = input_data[:, :, 2]
    mix_slice_data[:, :, 2] = input_data[:, :, 3]
    mix_slice_data[:, :, 3] = input_data[:, :, 7]
    mix_slice_data[:, :, 4] = input_data[:, :, -1]
    max_mix_data = np.max(mix_slice_data, axis=2)
    NDPI_data = (B11_data - max_mix_data) / (B11_data + 1e-10)

    return NDPI_data


def postprocess_NDPI(NDPI_data, threshold):
    """
    Perform binary segmentation on the NDPI heatmap using the threshold
    """
    new_NDPI_data = np.zeros_like(NDPI_data)
    new_NDPI_data[NDPI_data >= threshold] = 1
    new_NDPI_data[NDPI_data < threshold] = 0

    return new_NDPI_data


def find_best_threshold(NDPI_data, mode=None, bins=200, range_min=-0.5, range_max=0.5,
                        height=2, distance=5, prominence=0.5, min_threshold=0.02):
    """
    Find the optimal binary segmentation threshold
    """
    data = NDPI_data.flatten()
    counts, bin_edges = np.histogram(data, bins=bins, density=True, range=(range_min, range_max))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    # use find_peaks api to find peaks in histogram
    peaks, _ = find_peaks(counts, height=height, distance=distance, prominence=prominence)
    peaks_sorted = peaks[np.argsort(bin_centers[peaks])]

    if mode == 'new':
        filter_peaks_sorted = []
        for peak_idx in peaks_sorted:
            peak_x = bin_centers[peak_idx]
            if peak_x > min_threshold:
                filter_peaks_sorted.append(peak_idx)
        peaks_sorted = filter_peaks_sorted
        peak_nums = len(peaks_sorted)
        if peak_nums >= 2:
            if peak_nums > 2:
                start_idx = peaks_sorted[-3] + 1
                end_idx = peaks_sorted[-2]
            else:
                start_idx = peaks_sorted[-2] + 1
                end_idx = peaks_sorted[-1]
            valley_section = counts[start_idx:end_idx]
            valley_idx_in_section = np.argmin(valley_section)
            valley_idx = start_idx + valley_idx_in_section
            valley_x = bin_centers[valley_idx]
        else:
            valley_x = data.mean()  # failed to find an appropriate threshold

    if mode == 'old':
        if len(peaks_sorted) >= 2:
            start_idx = peaks_sorted[-2] + 1
            end_idx = peaks_sorted[-1]
            valley_section = counts[start_idx:end_idx]
            valley_idx_in_section = np.argmin(valley_section)
            valley_idx = start_idx + valley_idx_in_section
            valley_x = bin_centers[valley_idx]
        else:
            valley_x = data.mean()  # Failed to find an appropriate threshold

    return valley_x


def ANDPI_process_with_mask(img_data, mask_data, mode, ratio=None):
    """
    ANDPI process
    """
    NDPI_data = calculate_NDPI(img_data)
    # show_heatmap(NDPI_data)
    filter_NDPI_data = NDPI_data[mask_data > 0]
    # calculate_frequency_histogram_2d(filter_NDPI_data)
    threshold = find_best_threshold(filter_NDPI_data, mode=mode)
    new_NDPI_data = postprocess_NDPI(NDPI_data, threshold)
    new_NDPI_data[mask_data == 0] = 0
    if ratio:
        previous_num = np.sum(mask_data > 0)
        this_num = np.sum(new_NDPI_data > 0)
        remain_ratio = this_num / previous_num
        if remain_ratio < ratio:
            return mask_data

    return new_NDPI_data * np.max(mask_data)
