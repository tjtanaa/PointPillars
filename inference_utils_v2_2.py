import numpy as np
import cv2 as cv
from typing import List
from config_v2_2 import Parameters
from point_pillars_custom_processors_v2_2 import DataProcessor


class BBox(tuple):
    """ bounding box tuple that can easily be accessed while being compatible to cv2 rotational rects """

    def __new__(cls, bb_x, bb_y, bb_z, bb_length, bb_width, bb_height, bb_yaw, bb_heading, bb_cls, bb_conf):
        bbx_tuple = ((float(bb_x), float(bb_y)), (float(bb_length), float(bb_width)), float(np.rad2deg(bb_yaw)))
        return super(BBox, cls).__new__(cls, tuple(bbx_tuple))

    def __init__(self, bb_x, bb_y, bb_z, bb_length, bb_width, bb_height, bb_yaw, bb_heading, bb_cls, bb_conf):
        self.x = bb_x
        self.y = bb_y
        self.z = bb_z
        self.length = bb_length
        self.width = bb_width
        self.height = bb_height
        self.yaw = bb_yaw
        self.heading = bb_heading
        self.cls = bb_cls
        self.conf = bb_conf

    def __str__(self):
        return "BB | Cls: %s, x: %f, y: %f, l: %f, w: %f, yaw: %f" % (
            self.cls, self.x, self.y, self.length, self.width, self.yaw)


def rotational_nms(set_boxes, confidences, occ_threshold=0.7, nms_iou_thr=0.5):
    """ rotational NMS
    set_boxes = size NSeqs list of size NDet lists of tuples. each tuple has the form ((pos, pos), (size, size), angle)
    confidences = size NSeqs list of lists containing NDet floats, i.e. one per detection
    """
    assert len(set_boxes) == len(confidences) and 0 < occ_threshold < 1 and 0 < nms_iou_thr < 1
    if not len(set_boxes):
        return []
    assert (isinstance(set_boxes[0][0][0][0], float) or isinstance(set_boxes[0][0][0][0], int)) and \
           (isinstance(confidences[0][0], float) or isinstance(confidences[0][0], int))
    nms_boxes = []
    for boxes, confs in zip(set_boxes, confidences):
        assert len(boxes) == len(confs)
        indices = cv.dnn.NMSBoxesRotated(boxes, confs, occ_threshold, nms_iou_thr)
        print(indices)
        indices = indices.reshape(len(indices)).tolist()
        nms_boxes.append([boxes[i] for i in indices])
    return nms_boxes


def generate_bboxes_from_pred(occ, pos, siz, ang, hdg, clf, anchor_dims, occ_threshold=0.5):
    """ Generating the bounding boxes based on the regression targets """

    # Get only the boxes where occupancy is greater or equal threshold.
    real_boxes = np.where(occ >= occ_threshold)
    # Get the indices of the occupancy array
    coordinates = list(zip(real_boxes[0], real_boxes[1], real_boxes[2]))
    # Assign anchor dimensions as original bounding box coordinates which will eventually be changed
    # according to the predicted regression targets
    anchor_dims = anchor_dims
    real_anchors = np.random.rand(len(coordinates), len(anchor_dims[0]))

    for i, value in enumerate(real_boxes[2]):
        real_anchors[i, ...] = anchor_dims[value]

    # Change the anchor boxes based on regression targets, this is the inverse of the operations given in
    # createPillarTargets function (src/PointPillars.cpp)
    predicted_boxes = []
    for i, value in enumerate(coordinates):
        real_diag = np.sqrt(np.square(real_anchors[i][0]) + np.square(real_anchors[i][1]))
        real_x = value[0] * Parameters.x_step * Parameters.downscaling_factor + Parameters.x_min
        real_y = value[1] * Parameters.y_step * Parameters.downscaling_factor + Parameters.y_min
        bb_x = pos[value][0] * real_diag + real_x
        bb_y = pos[value][1] * real_diag + real_y
        bb_z = pos[value][2] * real_anchors[i][2] + real_anchors[i][3]
        # print(position[value], real_x, real_y, real_diag)
        bb_length = np.exp(siz[value][0]) * real_anchors[i][0]
        bb_width = np.exp(siz[value][1]) * real_anchors[i][1]
        bb_height = np.exp(siz[value][2]) * real_anchors[i][2]
        bb_yaw = ang[value] + real_anchors[i][4]
        # bb_yaw = -np.arcsin(np.clip(ang[value], -1, 1)) + real_anchors[i][4]
        bb_heading = np.round(hdg[value])
        bb_cls = np.argmax(clf[value])
        bb_conf = occ[value]
        predicted_boxes.append(BBox(bb_x, bb_y, bb_z, bb_length, bb_width, bb_height,
                                    bb_yaw, bb_heading, bb_cls, bb_conf))


    return predicted_boxes



def limit_period(val, offset=0.5, period=np.pi):
    return val - np.floor(val / period + offset) * period

def inverse_yaw_element(bb_yaw):
    bb_yaw -= np.pi / 2
    while bb_yaw > np.pi:
        # print("larger than pi")
        bb_yaw -= (np.pi * 2)
    while bb_yaw < -np.pi:
        # print("smaller than -pi")
        bb_yaw += (np.pi * 2)

    return bb_yaw

    # if bb_yaw > np.pi /2:
    #     bb_yaw -= 2 * np.pi
    
    # bb_yaw += np.pi/2
    # return bb_yaw

def generate_bboxes_from_pred_and_np_array(occ, pos, siz, ang, hdg, clf, anchor_dims, occ_threshold=0.5):
    """ Generating the bounding boxes based on the regression targets """

    # Get only the boxes where occupancy is greater or equal threshold.
    real_boxes = np.where(occ >= occ_threshold)
    # print(occ.shape)
    # Get the indices of the occupancy array
    coordinates = list(zip(real_boxes[0], real_boxes[1], real_boxes[2]))
    # Assign anchor dimensions as original bounding box coordinates which will eventually be changed
    # according to the predicted regression targets
    anchor_dims = anchor_dims
    real_anchors = np.random.rand(len(coordinates), len(anchor_dims[0]))

    for i, value in enumerate(real_boxes[2]):
        real_anchors[i, ...] = anchor_dims[value]

    # Change the anchor boxes based on regression targets, this is the inverse of the operations given in
    # createPillarTargets function (src/PointPillars.cpp)
    predicted_boxes = []
    predicted_boxes_list = []
    for i, value in enumerate(coordinates):
        # print("coordinate ", i)
        real_diag = np.sqrt(np.square(real_anchors[i][0]) + np.square(real_anchors[i][1]))
        real_x = value[0] * Parameters.x_step * Parameters.downscaling_factor + Parameters.x_min
        real_y = value[1] * Parameters.y_step * Parameters.downscaling_factor + Parameters.y_min
        # print("i: ", i, "\tx: ", real_x, "\ty:", real_y)
        # print("i: ", i, "\tx: ", value[0], "\ty:", value[1])
        bb_x = pos[value][0] * real_diag + real_x
        bb_y = pos[value][1] * real_diag + real_y
        bb_z = pos[value][2] * real_anchors[i][2] + real_anchors[i][3]
        # print(position[value], real_x, real_y, real_diag)
        bb_length = np.exp(siz[value][0]) * real_anchors[i][0]
        bb_width = np.exp(siz[value][1]) * real_anchors[i][1]
        bb_height = np.exp(siz[value][2]) * real_anchors[i][2]
        bb_heading = np.round(hdg[value])
        bb_yaw = ang[value] + real_anchors[i][4]
        # if np.int32(bb_heading) == 0:
        #     bb_yaw -= np.pi

        bb_cls = np.argmax(clf[value])
        bb_conf = occ[value]
        predicted_boxes.append(BBox(bb_x, bb_y, bb_z, bb_length, bb_width, bb_height,
                                    bb_yaw, bb_heading, bb_cls, bb_conf))
        predicted_boxes_list.append([bb_x, bb_y, bb_z, bb_length, bb_width, bb_height,
                                    bb_yaw, bb_heading, bb_cls, bb_conf])

    return predicted_boxes, np.array(predicted_boxes_list)

def convert_boxes_to_list(set_boxes):
    # (B, N)
    batch_predicted_boxes_list = []
    for batch_idx in range(len(set_boxes)):
        predicted_boxes_list = []

        for box in set_boxes[batch_idx]:

            predicted_boxes_list.append([box.x, box.y, box.z, box.length, box.width, box.height,
                                            box.yaw, box.heading, box.cls, box.conf])

        batch_predicted_boxes_list.append(predicted_boxes_list)
    return batch_predicted_boxes_list


def focal_loss_checker(y_true, y_pred, n_occs=-1):
    y_true = np.stack(np.where(y_true == 1))
    if n_occs == -1:
        n_occs = y_true.shape[1]
    occ_thr = np.sort(y_pred.flatten())[-n_occs]
    y_pred = np.stack(np.where(y_pred >= occ_thr))
    p = 0
    for gt in range(y_true.shape[1]):
        for pr in range(y_pred.shape[1]):
            if np.all(y_true[:, gt] == y_pred[:, pr]):
                p += 1
                break
    print("#matched gt: ", p, " #unmatched gt: ", y_true.shape[1] - p, " #unmatched pred: ", y_pred.shape[1] - p,
          " occupancy threshold: ", occ_thr)
