# DAT webclientDAT

## Overview

The Web Client DAT allows you to send HTTP requests to web servers from TouchDesigner. It supports GET, POST, PUT, DELETE, HEAD, OPTIONS and PATCH http methods.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Toggles the operator on/off. |
| `reqmethod` | Request Method | Menu | Selects the HTTP request method. |
| `url` | URL | Str | The URL of the server to send the HTTP request. Generally, if sending an HTTP request to a secure server, then the URL should begin with "https://". |
| `uploadfile` | Upload File | Str | The contents of the upload file will be sent to the server (chunked, if necessary). |
| `request` | Request | Pulse | Sends the request |
| `stop` | Stop | Pulse | Stops the stream of data from the server. |
| `stream` | Stream | Toggle | Enables streaming. This is only necessary to enable if the server support streaming. |
| `verifycert` | Verify Certificate (SSL) | Toggle | Enables TLS (transport layer security) certificate verification. |
| `timeout` | Timeout | Int | Timeout of the request if no response is received from the web server. |
| `includeheader` | Include Header in Output | Toggle | Includes the header in the output of the response. |
| `authtype` | Authentication Type | Menu | The type of authentication. |
| `username` | Username | Str | Username used in Basic/Digest authentication. |
| `pw` | Password | Str | Password used in Basic/Digest authentication. |
| `appkey` | App Key | Str | OAuth1 App Key retrieved from web server. |
| `appsecret` | App Secret | Str | OAuth1 App Secret retrieved from web server. |
| `oauthtoken` | User OAuth Token | Str | OAuth1 user token retrieved from web server. |
| `oauthsecret` | User OAuth Secret | Str | OAuth1 user secret retrieved from web server. |
| `clientid` | Client ID | Str | OAuth2 Client ID retrieved from web server. |
| `token` | Token | Str | OAuth2 token retrieved from web server. |
| `clear` | Clear Output | Pulse | Clears the output of the DAT. |
| `clamp` | Clamp Output as Rows | Toggle | When enabled, the output of the DAT is table instead of text. The rows will also be clamped to Maximum lines parameter value. This should be enabled when streaming is enabled too ensure that the ou... |
| `maxlines` | Maximum Lines | Int | The maximum number of rows when clamping is enabled. |
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT webclientDAT operator
webclientdat_op = op('webclientdat1')

# Get/set parameters
freq_value = webclientdat_op.par.active.eval()
webclientdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
webclientdat_op = op('webclientdat1')
output_op = op('output1')

webclientdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(webclientdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **27** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
