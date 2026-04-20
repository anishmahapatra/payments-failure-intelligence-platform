class AppError(Exception):
    status_code = 500
    code = "application_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ModelNotReadyError(AppError):
    status_code = 503
    code = "model_not_ready"


class FeatureLookupError(AppError):
    status_code = 500
    code = "feature_lookup_error"


class JobNotFoundError(AppError):
    status_code = 404
    code = "job_not_found"


class BatchProcessingError(AppError):
    status_code = 500
    code = "batch_processing_error"

