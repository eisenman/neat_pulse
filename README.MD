This integration brings Neat device sensor data into Home Assistant:
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
A read-only API key can be created from the Neat Pulse Settings menu for any org that has API entitlement.

The API polling interval defaults to 6 seconds in const.py and can be changed in the integration options once a device is added.

Neat Pulse API Details:

https://pulse.neat.no/apidocs/#api-Endpoints-endpointsSensorData

https://pulse.neat.no/apidocs/#api-Endpoints-endpointsGet
