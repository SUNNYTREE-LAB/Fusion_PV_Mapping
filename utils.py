import os
import cv2
import copy
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


def mask_intersection(mask1, mask2):
    """
    Compute the intersection of two 2D mask arrays
    """
    mask1_bool = np.asarray(mask1).astype(bool)
    mask2_bool = np.asarray(mask2).astype(bool)

    return (mask1_bool & mask2_bool).astype(np.int16) * np.max(mask1)


def mask_union(mask1, mask2):
    """
    Compute the union of two 2D mask arrays
    """
    mask1_bool = np.asarray(mask1).astype(bool)
    mask2_bool = np.asarray(mask2).astype(bool)

    return (mask1_bool | mask2_bool).astype(np.int16) * np.max(mask1)


def mask_diffreence(mask1, mask2):
    """
    Compute the difference of two 2D mask arrays,
    the result that is in mask2 but not in mask1
    """
    mask1_bool = np.asarray(mask1).astype(bool)
    mask2_bool = np.asarray(mask2).astype(bool)

    return (mask2_bool & (~mask1_bool)).astype(np.int16) * np.max(mask2)


def get_palette():
    """
    Get palette colors for binary segmentation visualization.
    """
    color_map = {
        "100": (255, 255, 255)  # 白色，测试用
    }
    palette = [0] * 768
    for idx, (label_id, color) in enumerate(color_map.items()):
        if label_id == '100':
            idx = 100
        palette[idx * 3] = color[0]  # R
        palette[idx * 3 + 1] = color[1]  # G
        palette[idx * 3 + 2] = color[2]  # B

    return palette


def save_mask(label_mask, output_path):
    """
    Save the binary segmentation results
    """
    palette = get_palette()
    label_mask = Image.fromarray(label_mask)
    label_mask = label_mask.convert('P')
    label_mask.putpalette(palette)
    label_mask.save(output_path)


def remove_small_areas(mask, max_area=5):
    """
    Remove connected components with an area less than 5
    """
    modify_mask = mask.copy()
    unique_values = np.unique(mask)
    for value in unique_values:
        if value == 0:
            continue
        binary_mask = np.uint8(mask == value)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area > max_area:
                continue
            modify_mask[labels == i] = 0

    return modify_mask


def show_heatmap(data, min_value=-1, max_value=1):
    """
    Plot and display the NDPI heatmap
    """
    colors = ["green", "yellow", "red"]
    cmap = LinearSegmentedColormap.from_list("BlueYellowRed", colors)
    fig, ax = plt.subplots(figsize=(10, 8))
    # draw heatmap
    im = ax.imshow(
        data,
        cmap=cmap,
        vmin=min_value, vmax=max_value
    )
    # add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("NDPI value", rotation=-90, va="bottom")
    ax.set_title("PV Heatmap（range：0-1）")
    plt.tight_layout()
    plt.show()


def calculate_frequency_histogram_2d(array_2d, bins=200):
    """
    Compute the frequency distribution histogram of the 2D array
    """
    flat_array = array_2d.flatten()
    plt.figure(figsize=(10, 6))
    plt.hist(flat_array, bins=bins, density=True, alpha=0.7, color='skyblue', edgecolor='navy')
    plt.xlim(-1, 1)
    plt.xlabel('NDPI value')
    plt.ylabel('Probability Density')
    plt.title('Probability density distribution of NDPI')
    plt.grid(True, alpha=0.3)
    plt.show()


def get_connected_components_by_mask(binary_mask, external_thr=1, internal_thr=1):
    """
    Extract the internal and external contours of PV
    """
    contours, hierarchy = cv2.findContours(
        binary_mask,
        cv2.RETR_TREE,
        cv2.CHAIN_APPROX_SIMPLE
    )
    connected_components = []
    if hierarchy is not None:
        hierarchy = hierarchy[0]
        processed = set()
        for i, cnt in enumerate(contours):
            if i in processed or hierarchy[i][3] != -1:
                continue
            external_contour = cnt
            external_area = cv2.contourArea(external_contour)
            if external_area < external_thr:
                continue
            component = {
                'external_contour': cnt,
                'internal_contours': []
            }

            child_idx = hierarchy[i][2]
            while child_idx != -1:
                internal_contour = contours[child_idx]
                internal_area = cv2.contourArea(internal_contour)
                if internal_area >= internal_thr:
                    component['internal_contours'].append(internal_contour)
                processed.add(child_idx)
                child_idx = hierarchy[child_idx][0]
            connected_components.append(component)

    return connected_components


def vis_results(rgb_path, old_mask_path, new_mask_path, pv_path):
    """
    Visualization PV extraction results
    """
    rgb_img = cv2.imread(rgb_path)
    # vis initial datas im rgb image
    raw_img = copy.deepcopy(rgb_img)
    raw_result_path = os.path.join(pv_path, "raw_datas.jpg")
    new_mask = np.array(Image.open(new_mask_path))
    new_components = get_connected_components_by_mask(new_mask)
    for i, comp in enumerate(new_components):
        cv2.drawContours(raw_img, [comp['external_contour']], -1, (0, 255, 0), 2)
    if os.path.exists(old_mask_path):
        old_mask = np.array(Image.open(old_mask_path))
        old_components = get_connected_components_by_mask(old_mask)
        for i, comp in enumerate(old_components):
            cv2.drawContours(raw_img, [comp['external_contour']], -1, (49, 125, 237), 2)
    cv2.imwrite(raw_result_path, raw_img)

    # vis final results in rgb image
    final_img = copy.deepcopy(rgb_img)
    final_img_path = os.path.join(pv_path, 'final_result.jpg')
    mask_path = os.path.join(pv_path, 'mask.png')
    final_mask = np.array(Image.open(mask_path))
    final_components = get_connected_components_by_mask(final_mask, external_thr=10, internal_thr=5)
    for i, comp in enumerate(final_components):
        cv2.drawContours(final_img, [comp['external_contour']], -1, (0, 0, 255), 2)
        cv2.drawContours(final_img, comp['internal_contours'], -1, (240, 0, 148), 1)
    cv2.imwrite(final_img_path, final_img)
