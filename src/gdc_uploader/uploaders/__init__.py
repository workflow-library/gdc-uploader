"""GDC Uploader implementations using the new architecture."""

from .standard import StandardUploader
from .api import APIUploader
from .spot import SpotUploader
from .single import SingleFileUploader

__all__ = [
    "StandardUploader",
    "APIUploader", 
    "SpotUploader",
    "SingleFileUploader"
]