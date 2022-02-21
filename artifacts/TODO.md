### Priority TODO List

- [x] Close single position and record to DB  
- [x] Telegram integration
- [x] Code Open range Breakout Strategy
- [x] Add High volume ETFs to Watchlist
- [x] Implement Growth % every day in Chat Service
- [x] Dockerize the service
- [ ] Build UI for viewing stocks 
- [ ] Backtesting strategies: VectorBT
- [ ] Analyze strategy and optimize   
- [ ] Save Time series to local DB
- [ ] Remove UI layer and build separate Vue.js frontend service 
- [ ] Develop Trading UI: Ref: https://www.youtube.com/watch?v=SVyuxZqbOrE&list=PLvzuUVysUFOuoRna8KhschkVVUo2E2g6G&index=7


### Important references

- Create command buttons for Telegram : https://stackoverflow.com/questions/34457568/how-to-show-options-in-telegram-bot
- Pattern Recognition API: https://finnhub.io/docs/api/pattern-recognition
- Easy Python Client example: https://github.com/Finnhub-Stock-API/finnhub-python
- String formatter: https://www.learnbyexample.org/python-string-format-method/
- Convert string to Python class: https://stackoverflow.com/questions/1176136/convert-string-to-python-class-object
- Install TA-Lib: https://sachsenhofer.io/install-ta-lib-ubuntu-server/
- SSH into a stopped container: docker run -it --rm --name newname vyapari_backend:latest bash
- Vue.js template : https://dev.to/markc86/50-awesome-vuejs-templates-and-themes-1pln
  https://bootstrap-vue.org/themes
- Market Edge Strategy: https://www.marketedge.com/MarketEdge/Help/techTerm.htm 

### Building Base Docker image commands:
- go into the artifacts directory
- `docker build -t qlikstar/python-39-ta-lib:<version> .`
- `docker push qlikstar/python-39-ta-lib:<version>`