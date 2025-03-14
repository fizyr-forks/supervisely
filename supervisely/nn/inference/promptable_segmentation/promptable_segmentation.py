from typing import Dict, List, Any
from supervisely.geometry.bitmap import Bitmap
from supervisely.nn.prediction_dto import PredictionMask
from supervisely.annotation.label import Label
from supervisely.sly_logger import logger
from supervisely.nn.inference.inference import Inference
from supervisely.decorators.inference import process_image_sliding_window


class PromptableSegmentation(Inference):
    def get_info(self) -> dict:
        info = super().get_info()
        info["task type"] = "promptable segmentation"
        return info

    def _get_obj_class_shape(self):
        return Bitmap

    def _create_label(self, dto: PredictionMask):
        obj_class = self.model_meta.get_obj_class(dto.class_name)
        if obj_class is None:
            raise KeyError(
                f"Class {dto.class_name} not found in model classes {self.get_classes()}"
            )
        if not dto.mask.any():  # skip empty masks
            logger.debug(f"Mask of class {dto.class_name} is empty and will be skipped")
            return None
        geometry = Bitmap(dto.mask)
        label = Label(geometry, obj_class)
        return label

    def predict(self, image_path: str, settings: Dict[str, Any]) -> List[PredictionMask]:
        raise NotImplementedError("Have to be implemented in child class")

    def predict_raw(self, image_path: str, settings: Dict[str, Any]) -> List[PredictionMask]:
        raise NotImplementedError(
            "Have to be implemented in child class If sliding_window_mode is 'advanced'."
        )
    
    @process_image_sliding_window
    def _inference_image_path(
        self,
        image_path: str,
        settings: Dict,
        data_to_return: Dict,  # for decorators
    ):
        inference_mode = settings.get("inference_mode", "full_image")
        logger.debug(
            "Inferring image_path:", extra={"inference_mode": inference_mode, "path": image_path}
        )

        if inference_mode == "sliding_window" and settings["sliding_window_mode"] == "advanced":
            predictions = self.predict_raw(image_path=image_path, settings=settings)
        else:
            predictions = self.predict(image_path=image_path, settings=settings)
        ann = self._predictions_to_annotation(image_path, predictions)

        logger.debug(
            f"Inferring image_path done. pred_annotation:",
            extra=dict(w=ann.img_size[1], h=ann.img_size[0], n_labels=len(ann.labels)),
        )
        return ann