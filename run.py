# -*- coding: utf-8 -*-

# * Copyright (c) 2009-2019. Authors: see NOTICE file.
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *      http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import os
import cv2
import logging
import numpy as np
from tempfile import TemporaryDirectory
from cytomine import CytomineJob
from cytomine.models import ImageInstance, ImageInstanceCollection, AnnotationCollection, Annotation
from cytomine.utilities.software import parse_domain_list
from shapely.geometry import Polygon
from sldc.locator import mask_to_objects_2d
from shapely.affinity import affine_transform
from skimage.filters import threshold_otsu

__author__ = "WSHMunirah WAhmad <wshmunirah@gmail.com>"



# def localThresholdWithMask(image, mask, block_size=11, delta=0):
#   """Approximate cv2.adaptiveThreshold with a Gaussian filter but with a binary mask excluding areas of the image.
#   These areas should not be considered for computing the thresholds.
  
#   Parameters
#   ----------
#   image: ndarray
#     The image to threshold
#   mask: ndarray
#     The image mask (only `True` pixels should be considered)
#   block_size: int
#     The size of the neighbourhood for threshold evaluation
#   delta: float
#     Constant subtracted from the mean or weighted mean.

#   Returns
#   -------
#   thresh_mask: ndarray
#     The thresholded mask
#   """
#   image[np.logical_not(mask)] = 0
  
#   kernel1d = cv2.getGaussianKernel(block_size, sigma=-1)
#   kernel2d = np.matmul(kernel1d, kernel1d.transpose())
  
#   # compute gaussian thresholds with a mask
#   sums = cv2.filter2D(
#     image.astype(float), 
#     ddepth=-1, 
#     kernel=kernel2d, 
#     borderType=cv2.BORDER_ISOLATED|cv2.BORDER_REPLICATE
#   )
#   divs = cv2.filter2D(
#     mask.astype(float), 
#     ddepth=-1, 
#     kernel=kernel2d, 
#     borderType=cv2.BORDER_ISOLATED|cv2.BORDER_REPLICATE
#   )
#   masked_means = sums / divs

#   # rectify with delta and remove masked pixels 
#   thresholds = masked_means - delta
#   thresh_mask = (image > thresholds).astype(np.uint8) * 255
#   thresh_mask[np.logical_not(mask)] = 255
#   return thresh_mask


def main(argv):
    with CytomineJob.from_cli(argv) as cj:
        
        images = ImageInstanceCollection()
        if cj.parameters.cytomine_id_images is not None:
            id_images = parse_domain_list(cj.parameters.cytomine_id_images)
            images.extend([ImageInstance().fetch(_id) for _id in id_images])
        else:
            images = images.fetch_with_filter("project", cj.parameters.cytomine_id_project)
        
        for image in cj.monitor(images, prefix="Running detection on image", period=0.1):
            # Resize image if needed
            resize_ratio = max(image.width, image.height) / cj.parameters.max_image_size
            if resize_ratio < 1:
                resize_ratio = 1

            resized_width = int(image.width / resize_ratio)
            resized_height = int(image.height / resize_ratio)

            bit_depth = image.bitDepth if image.bitDepth is not None else 8
            
            # download file in a temporary directory for auto-removal
            with TemporaryDirectory() as tmpdir:
                download_path = os.path.join(tmpdir, "{id}.png")
                image.dump(dest_pattern=download_path, max_size=max(resized_width, resized_height), bits=bit_depth)
                print("pass line 112")
                img = cv2.imread(image.filename, cv2.IMREAD_GRAYSCALE)
                # img = cv2.imread(download_path, cv2.IMREAD_GRAYSCALE)
                print("pass line 115")
                # unchanged = cv2.imread(image.filename, cv2.IMREAD_UNCHANGED)
                
                # mask = np.ones(img.shape, dtype=bool)
                # if unchanged.ndim == 3 and unchanged.shape[-1] in {2, 4}:  # has a mask
                #     mask = unchanged[:, :, -1].squeeze().astype(bool)
            
            # block_size = cj.parameters.threshold_blocksize
            # if block_size % 2 == 0:
            #     logging.warning(
            #         "The threshold block size must be an odd number! "
            #         "It will be incremented by one."
            #     )
            #     block_size += 1
            
            # thresholded_img = localThresholdWithMask(
            #     img, mask, 
            #     block_size=block_size, 
            #     delta=cj.parameters.threshold_constant
            # )

            # mask = thresholded_img
            # kernel = np.ones((5, 5), np.uint8)
            scale_percent = 1 # percent of original size
            width = int(img.shape[1] * scale_percent / 100)
            height = int(img.shape[0] * scale_percent / 100)
            dim = (width, height)
              
            # resize image
            im_resized = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
            print("pass line 145")
            # img[np.logical_not(mask)] = 0          
            pixels = np.array(im_resized).flatten()
            print("pass line 148")
            # print(max(pixels))
            threshold = threshold_otsu(pixels) + cj.parameters.threshold_blocksize
            print("pass line 151")
            # print(threshold)
            thresh_mask = (img < threshold).astype(np.uint8)*255
            print("pass line 154")
            # thresh_mask[np.logical_not(mask)] = 255
            kernel_size = np.array(cj.parameters.threshold_constant)
            print("pass line 157")
            if kernel_size.size != 2:  # noqa: PLR2004
              kernel_size = kernel_size.repeat(2)
            print("pass line 160")
            kernel_size = tuple(np.round(kernel_size).astype(int))
            print("pass line 162")
            # Create structuring element for morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, kernel_size)
            print("pass line 165")
            min_region_size = np.sum(kernel)
            print("pass line 167")
            _, output, stats, _ = cv2.connectedComponentsWithStats(thresh_mask, connectivity=8)
            print("pass line 169")
            sizes = stats[1:, -1]
            for i, size in enumerate(sizes):
                if size < min_region_size:
                    thresh_mask[output == i + 1] = 0
            print("pass line 174")

            thresh_mask = cv2.morphologyEx(thresh_mask, cv2.MORPH_DILATE, kernel)
            print("pass line 177")
            thresh_mask = cv2.bitwise_not(thresh_mask)
            print("pass line 179")
            # eroded_img = cv2.erode(thresholded_img, kernel, iterations=cj.parameters.erode_iterations)
            # dilated_img = cv2.dilate(eroded_img, kernel, iterations=cj.parameters.dilate_iterations)
  
            extension = 10
            extended_img = cv2.copyMakeBorder(
                thresh_mask,
                extension,
                extension,
                extension,
                extension,
                cv2.BORDER_CONSTANT,
                value=2 ** bit_depth
            )
            print("pass line 193")
            # extract foreground polygons 
            fg_objects = mask_to_objects_2d(extended_img, background=255, offset=(-extension, -extension))
            zoom_factor = image.width / float(resized_width)

            # Only keep components greater than {image_area_perc_threshold}% of whole image
            min_area = int((cj.parameters.image_area_perc_threshold / 100) * image.width * image.height)

            transform_matrix = [zoom_factor, 0, 0, -zoom_factor, 0, image.height]
            annotations = AnnotationCollection()
            for i, (fg_poly, _) in enumerate(fg_objects):
                upscaled = affine_transform(fg_poly, transform_matrix)
                if upscaled.area <= min_area:
                    continue
                annotations.append(Annotation(
                    location=upscaled.wkt,
                    id_image=image.id,
                    id_terms=[cj.parameters.cytomine_id_predicted_term],
                    id_project=cj.parameters.cytomine_id_project
                ))

            annotations.save()

        cj.job.update(statusComment="Finished.")


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])


# docker run -v $(pwd)/data:/images --entrypoint /bin/bash --rm -it segment-cv-adaptthres-sample:dev.rm.v0.0.13
# python run.py --host https://dev-apps.cytom.in --public_key "074f2cd2-4d3d-4724-b7d4-94e8ea7d183b" --private_key "3542cac5-e928-4e84-a581-022cff2d59d7" --id_project 818 --id_software 32170  --cytomine_id_images 71851 --cytomine_id_predicted_term 884 --max_image_size 2048  --threshold_blocksize 951 --threshold_constant 5 --erode_iterations 3 --dilate_iterations 3 --image_area_perc_threshold 5
