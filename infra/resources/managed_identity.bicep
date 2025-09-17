@description('Resource name suffix.')
param suffix string

@description('Name of Managed Identity resource.')
param name string = 'id-${suffix}'

@description('Location for all resources.')
param location string = resourceGroup().location

//----------- Managed Identity Resource -----------//
resource managed_identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
}

//----------- Outputs -----------//
output name string = managed_identity.name
