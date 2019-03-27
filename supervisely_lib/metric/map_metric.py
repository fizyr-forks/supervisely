# coding: utf-8

from collections import namedtuple

from supervisely_lib.sly_logger import logger
from supervisely_lib.metric.common import log_head, log_line, TOTAL_GROUND_TRUTH
from supervisely_lib.metric.matching import filter_labels_by_name, match_labels_by_iou
from supervisely_lib.metric.metric_base import MetricsBase

import numpy as np

MATCHES = 'matches'
AP = 'average-precision'

MatchWithConfidence = namedtuple('MatchWithConfidence', ['is_correct', 'confidence'])


class MAPMetric(MetricsBase):

    def __init__(self, class_mapping, iou_threshold):
        if len(class_mapping) < 1:
            raise RuntimeError('At least one classes pair should be defined!')
        self._gt_to_pred_class_mapping = class_mapping.copy()
        self._predicted_class_names = set(class_mapping.values())
        self._iou_threshold = iou_threshold
        self._counters = {
            gt_cls: {MATCHES: [], TOTAL_GROUND_TRUTH: 0} for gt_cls in self._gt_to_pred_class_mapping.keys()}

    @staticmethod
    def _get_confidence_value(label):
        return label.tags['confidence'].value if 'confidence' in label.tags else None

    def add_pair(self, ann_gt, ann_pred):
        labels_gt = filter_labels_by_name(ann_gt.labels, self._gt_to_pred_class_mapping)
        labels_pred = [label for label in filter_labels_by_name(ann_pred.labels, self._predicted_class_names)
                       if self._get_confidence_value(label) is not None]
        match_result = match_labels_by_iou(labels_1=labels_gt, labels_2=labels_pred, img_size=ann_gt.img_size,
                                           iou_threshold=self._iou_threshold)
        for match in match_result.matches:
            gt_class = match.label_1.obj_class.name
            label_pred = match.label_2
            self._counters[gt_class][MATCHES].append(
                MatchWithConfidence(is_correct=(label_pred.obj_class.name == self._gt_to_pred_class_mapping[gt_class]),
                                    confidence=self._get_confidence_value(label_pred)))
        for label_1 in labels_gt:
            self._counters[label_1.obj_class.name][TOTAL_GROUND_TRUTH] += 1

    @staticmethod
    def _calculate_average_precision(pair_name, pair_counters):
        if len(pair_counters[MATCHES] == 0):
            logger.warning('No samples for pair {!r} have been detected. '
                           'MAP value for this pair will be set to 0.'.format(pair_name))
            return 0

        sorted_matches = sorted(pair_counters[MATCHES], key=lambda match: match.confidence)
        correct_indicators = [int(match.is_correct) for match in sorted_matches]
        total_correct = np.cumsum(correct_indicators)
        recalls = total_correct / pair_counters[TOTAL_GROUND_TRUTH]
        precisions = total_correct / (np.arange(len(correct_indicators)) + 1)
        anchor_precisions = []
        for anchor_recall in np.linspace(0, 1, 11):
            points_above_recall = (recalls >= anchor_recall)
            anchor_precisions.append(np.max(precisions[points_above_recall]) if len(points_above_recall) > 0 else 0)
        return np.mean(anchor_precisions)

    def get_metrics(self):  # Macro-evaluation
        logger.info('Start evaluation of macro metrics.')
        result = {pair_name: {AP: self._calculate_average_precision(pair_name, pair_counters)}
                  for pair_name, pair_counters in self._counters.items()}
        logger.info('Finish macro evaluation')
        return result

    @staticmethod
    def average_per_class_avg_precision(per_class_metrics):
        return np.mean(class_metrics[AP] for class_metrics in per_class_metrics.values())

    def get_total_metrics(self):
        return self.average_per_class_avg_precision(self.get_metrics())

    def log_total_metrics(self):
        log_line()
        log_head(' Result metrics values for {} IoU threshold '.format(self._iou_threshold))

        classes_values = self.get_metrics()
        for i, (cls_gt, pair_values) in enumerate(classes_values.items()):
            average_precision = pair_values[AP]
            log_line()
            log_head(' Results for pair of classes <<{} <-> {}>>  '.format(cls_gt,
                                                                           self._gt_to_pred_class_mapping[cls_gt]))
            logger.info('Average Precision (AP): {}'.format(average_precision))

        log_line()
        log_head(' Mean metrics values ')
        logger.info('Mean Average Precision (mAP): {}'.format(self.average_per_class_avg_precision(classes_values)))
        log_line()
