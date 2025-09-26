# DAT webserverDAT

## Overview

The Text DAT lets you edit free-form, multi-line ASCII text.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Starts and Stops the webserver. |
| `restart` | Restart | Pulse | When the server is active, pulsing will restart it. |
| `port` | Port | Int | The web server's connection port. Eg. If the port number is 9980, the web server can be connected to locally (via a web browser) at the address "localhost:9980". |
| `secure` | Secure (TLS) | Toggle | When enabled, the web server will use transport layer security (TLS) to create secure connections with clients. As a result, the web server will run through HTTPS instead of HTTP. |
| `privatekey` | Private Key File Path | File | The path to the private key file of the server's TLS certificate. |
| `certificate` | Certificate File Path | File | The path to the certificate file of the server's TLS certificate. |
| `password` | Certificate Password | Text | The password for the certificate specified above. The password is only visually hidden and can still be accessed via python. In order to protect it and encrypt it when the project is saved, the Web... |
| `callbacks` | Callbacks DAT | DAT | A reference to a DAT with python callbacks. The Web Server DAT relies heavily on the Callbacks DAT, and in fact most functionality passes through the callbacks.   onHTTPRequest - Triggered when the... |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT webserverDAT operator
webserverdat_op = op('webserverdat1')

# Get/set parameters
freq_value = webserverdat_op.par.active.eval()
webserverdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
webserverdat_op = op('webserverdat1')
output_op = op('output1')

webserverdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(webserverdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
