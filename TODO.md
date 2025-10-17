# Caching Consistency Fix

## Overview
Fix caching consistency issues where updates/deletes to units or properties only clear landlord caches but not related property unit caches, leading to stale data.

## Tasks
- [ ] Modify CreateUnitView to clear property units cache after creating a unit
- [ ] Modify AssignTenantView to clear both landlord properties and property units caches after assigning tenant
- [ ] Modify UnitTypeListCreateView to clear both caches after creating units for a unit type
- [ ] Modify AdjustRentView to clear property units caches for affected properties after rent adjustments
- [ ] Modify TenantUpdateUnitView to clear landlord properties cache after tenant updates unit
- [ ] Modify UpdatePropertyView to clear property units cache after updating or deleting a property
- [ ] Modify UserCreateView to clear caches after creating properties and units for new landlord
