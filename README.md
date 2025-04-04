ca-pmda
=======

Python client for the CA Performance Management Data Aggregator data-driven API.

Installation
------------

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install
ca-pmda.

```
pip install git+https://github.com/mcdenis/ca-pmda.git
```

Usage
-----

```py
from requests import Session
from ca_pmda import DynamicClient, AttributeComparison, And, dynamic_model

with Session() as session:
    # Bootstrap client.
    session.auth = "my-user-name", "my-password"
    client = DynamicClient("the-hostname", "https", session)

    # Get first SNMP profile with the name "the-profile".
    profile_filter = AttributeComparison(
        "CommunicationProfile.ProfileName", "EQUAL", "the-profile")
    profile = next(client.filtered_get_list("profiles", profile_filter))

    # Get the active devices whose name ends with "_router".
    device_filter = And(
        AttributeComparison("ManageableDevice.SystemName", "ENDS_WITH", "_router"),
        AttributeComparison("Lifecycle.State", "EQUAL", "ACTIVE")
    )
    devices = client.filtered_get_list("devices/manageable", device_filter)

    # Update the afore queried devices to the afore queried SNMP profile.
    updated_devices = {
        d.ID: dynamic_model(
            "ManageableDevice", version="1.0.0", SNMPProfileID=profile.ID,
            SNMPProfileVersion="SNMPV3") # TODO profile may not be SNMPV3
        for d in devices
    }
    # TODO is there an interface for bulk requests?
    for device_id, device in updated_devices.items():
        client.update("devices/manageable", device_id, device)

```

Project Status
--------------

This software is not feature-complete and developed on a "as-needed" basis.