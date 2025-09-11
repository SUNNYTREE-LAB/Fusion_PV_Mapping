import skimage
import os
import cv2
from tqdm import tqdm
import numpy as np
from PIL import Image

from andpi import ANDPI_process_with_mask
from utils import mask_intersection, mask_union, mask_diffreence, save_mask, remove_small_areas, vis_results


def fusion_PV_with_ANDPI(tiff_path, rgb_path, old_mask_path, new_mask_path, save_dir):
    """
    ANDPI-based data fusion process
    """
    # read multi-spectral image
    img_data = skimage.io.imread(tiff_path)
    img_data = np.array(img_data) / 10000
    # read rgb image
    rgb_img = cv2.imread(rgb_path)
    assert img_data.shape[:2] == rgb_img.shape[:2]
    # read new pv mask
    new_mask = np.array(Image.open(new_mask_path))
    # check if an old mask exists: if it does, fuse the old and new masks; otherwise, directly process the new mask
    if os.path.exists(old_mask_path):  # fuse
        old_mask = np.array(Image.open(old_mask_path))
        old_final_mask = ANDPI_process_with_mask(img_data, old_mask, mode='old', ratio=0.8)
        diff_mask = mask_diffreence(old_mask, new_mask)
        diff_final_mask = ANDPI_process_with_mask(img_data, diff_mask, mode="new")
        final_mask = mask_union(old_final_mask, diff_final_mask)
    else:  # process new mask
        final_mask = ANDPI_process_with_mask(img_data, new_mask, mode="new")
    # morphological postprocessing
    final_mask = remove_small_areas(final_mask)
    save_mask(final_mask, os.path.join(save_dir, 'mask.png'))


if __name__ == '__main__':
    data_root = './datas'
    pv_names = os.listdir(data_root)
    for pv_name in tqdm(pv_names, total=len(pv_names)):
        pv_path = os.path.join(data_root, pv_name)
        file_name = '_'.join(pv_name.split('_')[1:])
        img_path = os.path.join(pv_path, f"{file_name}_full.tif")  # multi-spectral image of PV
        rgb_path = os.path.join(pv_path, f"{file_name}_rgb.jpg")  # RGB image used for visualization
        old_mask_path = os.path.join(pv_path, "old_mask.png")  # mask converted from ChinaPV/GlobalPV dataset
        new_mask_path = os.path.join(pv_path, "new_mask.png")  # mask converted from TZ-SAM dataset
        # fusion method
        fusion_PV_with_ANDPI(img_path, rgb_path, old_mask_path, new_mask_path, pv_path)

        # vis the initial datas and final results
        vis_results(rgb_path, old_mask_path, new_mask_path, pv_path)
