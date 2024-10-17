#temp works, timestamp, vocindex broken

import logging
from datetime import timedelta, datetime, timezone
from typing import Optional, Dict, Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    LIGHT_LUX,
)
from homeassistant.helpers import aiohttp_client
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_ACCESS_TOKEN,
    CONF_ORGANIZATION_ID,
    CONF_ENDPOINT_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)
from .api import NeatPulseAPI, NeatPulseAPIError, AuthenticationError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

# Mapping of sensor types to their units and device classes
SENSOR_CONFIG: Dict[str, Dict[str, Optional[str]]] = {
    "temp": {
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    "temperature": {
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    "humidity": {
        "unit": PERCENTAGE,
        "device_class": SensorDeviceClass.HUMIDITY,
    },
    "co2": {
        "unit": "ppm",
        "device_class": None,
    },
    "voc": {
        "unit": "ppb",
        "device_class": None,
    },
    "vocindex": {  # Added mapping for 'vocindex'
        "unit": None,
        "device_class": None,
    },
    "illumination": {
        "unit": LIGHT_LUX,
        "device_class": SensorDeviceClass.ILLUMINANCE,
    },
    "people": {
        "unit": "persons",
        "device_class": None,
    },
    "timestamp": {
        "unit": None,
        "device_class": SensorDeviceClass.TIMESTAMP,
    },
    # Add more sensor types as needed
}

# List of sensor types that do not require a unit
NO_UNIT_SENSORS = ["vocindex", "timestamp"]

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up Neat Pulse sensors from a config entry."""
    access_token = entry.data.get(CONF_ACCESS_TOKEN)
    organization_id = entry.data.get(CONF_ORGANIZATION_ID)
    endpoint_id = entry.data.get(CONF_ENDPOINT_ID)

    scan_interval = timedelta(
        minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    session = aiohttp_client.async_get_clientsession(hass)
    api = NeatPulseAPI(session, access_token, organization_id)

    coordinator = NeatPulseDataUpdateCoordinator(
        hass, api, endpoint_id, scan_interval
    )
    await coordinator.async_config_entry_first_refresh()

    entities = []
    endpoint = coordinator.data
    sensor_data = endpoint.get("sensor_data", {})
    if not sensor_data:
        _LOGGER.warning(f"No sensor data available for endpoint {endpoint_id}")
        return

    _LOGGER.debug(f"Processing sensor data: {sensor_data}")

    for sensor_type, value in sensor_data.items():
        sensor_type_clean = sensor_type.lower().strip()
        config = SENSOR_CONFIG.get(sensor_type_clean)

        if config:
            unit = config["unit"]
            device_class = config["device_class"]
        else:
            # Handle unknown sensor types gracefully
            _LOGGER.warning(
                f"Unknown sensor type '{sensor_type_clean}'. Skipping."
            )
            continue

        if device_class in [cls for cls in SensorDeviceClass] and not unit:
            _LOGGER.error(
                f"Sensor '{sensor_type_clean}' requires a unit but none provided. Skipping."
            )
            continue

        sensor_entity = NeatPulseSensor(
            coordinator=coordinator,
            endpoint_id=endpoint_id,
            sensor_type=sensor_type_clean,
            unit=unit,
            device_class=device_class,
        )
        entities.append(sensor_entity)
        _LOGGER.info(
            f"Added sensor entity '{sensor_entity.name}' with unit '{unit}' and device class '{device_class}'."
        )

    # Optionally add other sensors like 'inCallStatus'
    if "inCallStatus" in endpoint.get("details", {}):
        call_status_sensor = NeatPulseCallStatusSensor(
            coordinator=coordinator,
            endpoint_id=endpoint_id,
        )
        entities.append(call_status_sensor)
        _LOGGER.info(f"Added call status sensor entity '{call_status_sensor.name}'.")

    async_add_entities(entities)


class NeatPulseDataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to manage fetching data from Neat Pulse API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: NeatPulseAPI,
        endpoint_id: str,
        scan_interval: timedelta,
    ):
        """Initialize the coordinator."""
        self.api = api
        self.endpoint_id = endpoint_id
        super().__init__(
            hass,
            _LOGGER,
            name="Neat Pulse Data",
            update_interval=scan_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API."""
        try:
            sensor_data_response = await self.api.get_endpoint_sensor_data(
                self.endpoint_id
            )
            _LOGGER.debug(f"Sensor data response: {sensor_data_response}")
            endpoint_data = sensor_data_response.get("endpointData", {})
            data_points = endpoint_data.get("data", [])
            if not data_points:
                raise UpdateFailed("No data available from endpoint")

            latest_data_point = data_points[0]
            _LOGGER.debug(f"Latest data point: {latest_data_point}")

            # Log complete sensor data for debugging
            _LOGGER.info(f"Complete sensor_data: {latest_data_point}")

            # Convert numeric values to appropriate types
            for key, value in latest_data_point.items():
                key_lower = key.lower().strip()
                if key_lower != "timestamp" and key_lower not in NO_UNIT_SENSORS:
                    try:
                        latest_data_point[key_lower] = float(value)
                    except (TypeError, ValueError):
                        _LOGGER.warning(
                            f"Value for '{key}' is not a number: {value}"
                        )
                        latest_data_point[key_lower] = None
                elif key_lower == "timestamp":
                    try:
                        latest_data_point[key_lower] = int(value)
                    except (TypeError, ValueError):
                        _LOGGER.warning(
                            f"Value for 'timestamp' is not an integer: {value}"
                        )
                        latest_data_point[key_lower] = None

            # Fetch endpoint details
            endpoint_details = await self.api.get_endpoint_details(
                self.endpoint_id
            )
            _LOGGER.debug(f"Endpoint details: {endpoint_details}")

            room_name = endpoint_details.get("roomName") or endpoint_details.get(
                "name", f"Endpoint {self.endpoint_id}"
            )
            _LOGGER.debug(f"Using room name: {room_name}")

            return {
                "id": self.endpoint_id,
                "name": room_name,
                "sensor_data": latest_data_point,
                "details": endpoint_details,
            }

        except AuthenticationError as err:
            raise UpdateFailed(f"Authentication error: {err}") from err
        except NeatPulseAPIError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            _LOGGER.exception(f"Unexpected error during data update: {err}")
            raise UpdateFailed(f"Unexpected error: {err}") from err


class NeatPulseSensor(SensorEntity):
    """Representation of a Neat Pulse sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        endpoint_id: str,
        sensor_type: str,
        unit: Optional[str],
        device_class: Optional[str],
    ):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.endpoint_id = endpoint_id
        self.sensor_type = sensor_type
        self._unit = unit
        self._attr_device_class = device_class

        endpoint = coordinator.data
        self.device_name = endpoint["name"]
        self._attr_unique_id = f"{endpoint_id}_{sensor_type}"
        self._attr_name = f"{self.device_name} {sensor_type.replace('_', ' ').capitalize()}"

        # Set device info to group sensors under the endpoint
        self._attr_device_info = {
            "identifiers": {(DOMAIN, endpoint_id)},
            "name": self.device_name,
            "manufacturer": "Neat",
            "model": "Pulse Endpoint",
        }

        # Assign unit_of_measurement only if unit is not None
        if self._unit:
            self._attr_native_unit_of_measurement = self._unit
        else:
            # Check if device_class requires a unit
            if self._attr_device_class in SensorDeviceClass:
                _LOGGER.error(
                    f"Sensor '{self._attr_name}' requires a unit of measurement but none was provided."
                )
                raise HomeAssistantError(
                    f"Missing unit for sensor '{self._attr_name}'."
                )
            self._attr_native_unit_of_measurement = None  # Allowed for device classes that don't require units

        _LOGGER.debug(
            f"Sensor '{self._attr_name}' assigned unit: {self._unit}"
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self.coordinator.data["sensor_data"].get(self.sensor_type)
        _LOGGER.debug(
            f"Sensor '{self._attr_name}' raw value: {value}"
        )

        if value is None:
            _LOGGER.warning(
                f"No value found for sensor '{self.sensor_type}'"
            )
            return None

        try:
            if self.sensor_type == "timestamp":
                timestamp = int(value)
                # Handle timestamp in seconds or milliseconds
                if timestamp > 10000000000:
                    # If timestamp is in milliseconds, convert to seconds
                    timestamp = timestamp / 1000
                dt_value = datetime.fromtimestamp(
                    timestamp, tz=timezone.utc
                )
                return dt_value

            elif self.sensor_type in ["temp", "temperature", "humidity"]:
                return round(float(value), 2)

            elif self.sensor_type == "people":
                return int(float(value))

            else:
                # For other sensors, attempt to return as float
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return value

        except Exception as e:
            _LOGGER.error(
                f"Error processing sensor '{self.sensor_type}': {e}"
            )
            return None

    @property
    def should_poll(self):
        """Disable polling (handled by coordinator)."""
        return False

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class NeatPulseCallStatusSensor(SensorEntity):
    """Representation of the Neat Pulse inCallStatus sensor."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, endpoint_id: str
    ):
        """Initialize the call status sensor."""
        self.coordinator = coordinator
        self.endpoint_id = endpoint_id
        self.sensor_type = "inCallStatus"
        self._attr_device_class = None

        endpoint = coordinator.data
        self.device_name = endpoint["name"]
        self._attr_unique_id = f"{endpoint_id}_inCallStatus"
        self._attr_name = f"{self.device_name} In Call Status"

        # Set device info to group sensors under the endpoint
        self._attr_device_info = {
            "identifiers": {(DOMAIN, endpoint_id)},
            "name": self.device_name,
            "manufacturer": "Neat",
            "model": "Pulse Endpoint",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self.coordinator.data["details"].get("inCallStatus")
        _LOGGER.debug(
            f"Call Status Sensor '{self._attr_name}' value: {value}"
        )
        return value

    @property
    def should_poll(self):
        """Disable polling (handled by coordinator)."""
        return False

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:phone-off" if self.native_value == "NONE" else "mdi:phone"

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
