__all__ = ["MeasurementService"]


def __getattr__(name: str):
    if name == "MeasurementService":
        from keith_ivt.services.measurement_service import MeasurementService

        return MeasurementService
    raise AttributeError(name)
