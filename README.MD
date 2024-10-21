This HACS integration brings Neat device sensor data into Home Assistant:
- co2
- humidity
- illumination
- people count
- temperature
- voc
- vocIndex

Not all Neat devices have each of these sensors, so ymmv.

The values for the following are also returned:
- Call Status (NONE, ZOOM, TEAMS)
- Device Name

Once added to HACS, you will need the following details from Neat Pulse to add a device:
- Organization ID
- Read-only API Key
- Device ID for device to be added

The org id (7 characters) and device id (36 characters) are both visible in the Neat Pulse url path when viewing the details for any given device. 
A read-only API key can be created from the Neat Pulse Settings > API Keys menu for any org that has API entitlement.

The API polling interval defaults to 6 seconds in const.py and can be changed in the integration options once a device is added.

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=eisenman&repository=neat_pulse&category=Integration" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>

Neat Pulse API Details:

https://pulse.neat.no/apidocs/#api-Endpoints-endpointsSensorData

https://pulse.neat.no/apidocs/#api-Endpoints-endpointsGet
