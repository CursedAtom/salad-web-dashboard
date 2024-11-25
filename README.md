# salad-web-dashboard
Chef Dashboard for Salad with Web Interface


### Before running, ensure you install the requirements:
```cmd
pip install flask flask-cors bleach
```

## To run the webserver, you need to supply a machine name. The server port is optional. Default port is 8000.

```cmd
python.exe server.py -machine_name "Name of Machine"
```
<br>
or...<br>

```cmd
python.exe server.py -port 1000 -machine_name "Name of Machine"
```

#### The dashboard will be accessible from http://localhost:[port]

### Possible issues:
- Some desktop versions of chrome may decided to not work. If it says error loading data and you're using desktop chrome, try checking the console. It may say it tried to access a file rather than an api.
- ~~Bandwidth sharing may behave weirdly if you have multiple gateways in your log folder (idk, too lazy to fix)~~ just tested it, works fine
- First load will take a while (2-6 seconds) while the cache builds. subsequent loads should only take 300-600ms, sometimes longer if the page has not been loaded for a while.

#### Disclaimer: I AM IN NO WAY ASSOCIATED WITH SALAD TECHNOLOGIES. THIS IS A PERSONAL PROJECT THAT DOES NOT REPRESENT--OR ATTEMPT TO REPRESENT--THE COMPANY
