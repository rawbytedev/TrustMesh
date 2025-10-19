# Shipment

This is a guide detailing integration with shipment services

Note: TrustMesh is still experimental 

Each shipment service can regiester as a shipment provider to allow users to set escrow using realtime feeds. The integration is straight forward and doesn't require much setup but the requirement are as follow:

 - A server that has the ability to provide live feeds for shipments

then all to do is register the server and add support for the API used by trustMesh 
each shipment service gets a unique identifier currently 5 character
the len of a shipment ID can vary depending on the provider but the 5 first character are always the
identifier for the shipment Provider