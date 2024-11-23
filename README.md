# salad-web-dashboard
Chef Dashboard for Salad with Web Interface


### Before running, ensure you install the requirements:
```cmd
pip install flask flask-cors bleach
```

## To run the webserver, you need to supply a machine name. The server port is optional. Default port is 8000.

```python.exe server.py -machine_name "Name of Machine"```<br>
or...<br>
```python.exe server.py -port 1000 -machine_name "Name of Machine"``` to run on port 1000

### Known possible issues:
- Bandwidth sharing may behave weirdly if you have multiple gateways in your log folder (idk, too lazy to fix)
- First load will take a while (2-6 seconds) while the cache builds. subsequent loads should only take 300-600ms, sometimes longer if the page has not been loaded for a while.

#### Disclaimer: I AM IN NO WAY ASSOCIATED WITH SALAD TECHNOLOGIES. THIS IS A PERSONAL PROJECT THAT DOES NOT REPRESENT--OR ATTEMPT TO REPRESENT--THE COMPANY
