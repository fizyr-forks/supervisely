# coding: utf-8
import numpy as np

from supervisely_lib.geometry.constants import DATA, ORIGIN
from supervisely_lib.geometry.geometry import Geometry
from supervisely_lib.geometry.point import Point
from supervisely_lib.geometry.rectangle import Rectangle

from supervisely_lib.imaging.image import resize_inter_nearest, restore_proportional_size


def resize_origin_and_bitmap(origin: Point, bitmap: np.ndarray, in_size, out_size):
    new_size = restore_proportional_size(in_size=in_size, out_size=out_size)

    row_scale = new_size[0] / in_size[0]
    col_scale = new_size[1] / in_size[1]

    # TODO: Double check (+restore_proportional_size) or not? bitmap.shape and in_size are equal?
    # Make sure the resulting size has at least one pixel in every direction (i.e. limit the shrinkage to avoid having
    # empty bitmaps as a result).
    scaled_rows = max(round(bitmap.shape[0] * row_scale), 1)
    scaled_cols = max(round(bitmap.shape[1] * col_scale), 1)

    scaled_origin = Point(row=round(origin.row * row_scale), col=round(origin.col * col_scale))
    scaled_bitmap = resize_inter_nearest(bitmap, (scaled_rows, scaled_cols))
    return scaled_origin, scaled_bitmap


class BitmapBase(Geometry):
    def __init__(self, origin, data, expected_data_dims=None):
        """
        :param origin: Point
        :param data: np.ndarray
        """
        if not isinstance(origin, Point):
            raise TypeError('MultichannelBitmap "origin" argument must be "Point" object!')

        if not isinstance(data, np.ndarray):
            raise TypeError('MultichannelBitmap "data" argument must be numpy array object!')

        data_dims = len(data.shape)
        if expected_data_dims is not None and data_dims != expected_data_dims:
            raise ValueError('MultichannelBitmap "data" argument must be a {}-dimensional numpy array. ' +
                             'Instead got {} dimensions'.format(expected_data_dims, data_dims))

        self._origin = origin.clone()
        self._data = data.copy()

    @classmethod
    def _impl_json_class_name(cls):
        """Descendants must implement this to return key string to look up serialized representation in a JSON dict."""
        raise NotImplementedError()

    @staticmethod
    def base64_2_data(s: str) -> np.ndarray:
        raise NotImplementedError()

    @staticmethod
    def data_2_base64(data: np.ndarray) -> str:
        raise NotImplementedError()

    def to_json(self):
        return {
            self._impl_json_class_name(): {
                ORIGIN: [self.origin.col, self.origin.row],
                DATA: self.data_2_base64(self.data)
            }
        }

    @classmethod
    def from_json(cls, json_data):
        json_root_key = cls._impl_json_class_name()
        if json_root_key not in json_data:
            raise ValueError(
                'Data must contain {} field to create MultichannelBitmap object.'.format(json_root_key))

        if ORIGIN not in json_data[json_root_key] or DATA not in json_data[json_root_key]:
            raise ValueError('{} field must contain {} and {} fields to create MultichannelBitmap object.'.format(
                json_root_key, ORIGIN, DATA))

        col, row = json_data[json_root_key][ORIGIN]
        data = cls.base64_2_data(json_data[json_root_key][DATA])
        return cls(Point(row=row, col=col), data=data)

    @property
    def origin(self) -> Point:
        return self._origin.clone()

    @property
    def data(self) -> np.ndarray:
        return self._data.copy()

    def translate(self, drow, dcol):
        translated_origin = self.origin.translate(drow, dcol)
        return self.__class__(translated_origin, self.data)

    def fliplr(self, img_size):
        flipped_mask = np.flip(self.data, axis=1)
        flipped_origin = Point(row=self.origin.row, col=(img_size[1] - flipped_mask.shape[1] - self.origin.col))
        return self.__class__(flipped_origin, flipped_mask)

    def flipud(self, img_size):
        flipped_mask = np.flip(self.data, axis=0)
        flipped_origin = Point(row=(img_size[0] - flipped_mask.shape[0] - self.origin.row), col=self.origin.col)
        return self.__class__(flipped_origin, flipped_mask)

    def scale(self, factor):
        new_rows = round(self._data.shape[0] * factor)
        new_cols = round(self._data.shape[1] * factor)
        mask = self._resize_mask(self.data, new_rows, new_cols)
        origin = self.origin.scale(factor)
        return self.__class__(origin=origin, data=mask)

    @staticmethod
    def _resize_mask(mask, out_rows, out_cols):
        return resize_inter_nearest(mask.astype(np.uint8), (out_rows, out_cols)).astype(np.bool)

    def to_bbox(self):
        return Rectangle.from_array(self._data).translate(drow=self._origin.row, dcol=self._origin.col)
