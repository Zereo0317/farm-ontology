"""On-farm sensor ingest. Device JSON in, governed observation out."""

from farm_ontology.sensors.ingest import (
    DEVICE_CLASSES,
    ingest_device_json,
    ingest_record,
    sensor_support_disabled,
)
from farm_ontology.sensors.device_contract import (
    AcceptedMeasurement,
    DeviceContractGap,
    NormalizedMeasurement,
    PropertyBinding,
    SensorAdapterManifest,
    validate_normalized_measurement,
)
from farm_ontology.sensors.adapter_sdk import (
    AdapterRegistry,
    AdapterSdkError,
    LocalSensorOutbox,
    SensorAdapter,
    SyntheticSoilVwcAdapter,
    synthetic_soil_uplink,
)

__all__ = [
    "DEVICE_CLASSES",
    "ingest_device_json",
    "ingest_record",
    "sensor_support_disabled",
    "AcceptedMeasurement",
    "DeviceContractGap",
    "NormalizedMeasurement",
    "PropertyBinding",
    "SensorAdapterManifest",
    "validate_normalized_measurement",
    "AdapterRegistry",
    "AdapterSdkError",
    "LocalSensorOutbox",
    "SensorAdapter",
    "SyntheticSoilVwcAdapter",
    "synthetic_soil_uplink",
]
