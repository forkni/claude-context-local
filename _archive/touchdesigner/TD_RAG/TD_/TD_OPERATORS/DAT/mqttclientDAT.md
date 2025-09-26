# DAT mqttclientDAT

## Overview

The MQTT Client DAT receives and sends data from/to MQTT devices via MQTT servers (broker).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Enable the connection. |
| `netaddress` | Network Address | Str | The address of the broker to connect to. The address should take the form ://:. Accepted protocol URIs can include tcp, ssl, ws, and wss. |
| `specifyid` | Specify ID | Toggle | Allows naming the client with parameter User Client ID, otherwise automatically and uniquely generated for each connection. |
| `usercid` | User Client ID | Str | Client name when Specify ID enabled. |
| `keepalive` | Keep Alive Interval | Int | Specifies in seconds, the maximum time to expect without communication. If no data is sent during this time, a lightweight ping message is sent to the server instead. Can be set to 0 to avoid pings. |
| `maxinflight` | Max in Flight | Int | Controls how many messages can be in-flight simultaneously. |
| `cleansession` | Clean Session | Toggle | If Specify ID is selected, the server will preserve any state information associated with the connection of that ID, such as subscriptions, delivery attempts, etc. |
| `verifycert` | Verify Certificate | Toggle | Enables TLS (transport layer security) certificate verification against the server (ie. broker). |
| `username` | Username | String | Specify the username for authentication if the server requires it. MQTT servers that support the MQTT v3.1 protocol provide authentication and authorization via username and password. |
| `password` | Password | String | Specify the password for authentication if the server requires it. MQTT servers that support the MQTT v3.1 protocol provide authentication and authorization via username and password. |
| `reconnect` | Reconnect | Pulse | Will attempt to reconnect to the MQTT broker. |
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT contains functions that are called when connections are made, lost or published data arrives. See mqttclientDAT_Class for usage. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `fromop` | From Operator | OP | The operator whose state change will trigger the DAT to execute its script when Execute From is set to Specified Operator. This operator is also the path that the script will be executed from if th... |
| `clamp` | Clamp Output | Toggle | The DAT is limited to 100 messages by default but with Clamp Output, this can be set to anything including unlimited. |
| `maxlines` | Maximum Lines | Int | Limits the number of messages, older messages are removed from the list first. |
| `clear` | Clear Output | Pulse | Deletes all lines except the heading. To clear with a python script op("opname").par.clear.pulse() |
| `bytes` | Bytes Column | Toggle | Outputs the raw bytes of the message in a separate column. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT mqttclientDAT operator
mqttclientdat_op = op('mqttclientdat1')

# Get/set parameters
freq_value = mqttclientdat_op.par.active.eval()
mqttclientdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
mqttclientdat_op = op('mqttclientdat1')
output_op = op('output1')

mqttclientdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(mqttclientdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **22** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
