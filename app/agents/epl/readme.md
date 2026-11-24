# README for the epl agent

Example CLI Commands - for macOS and Linux.  The Windows PowerShell commands are similar.

```
Command:                                 Description
cd app/                                  cd to the app/ directory within the repository root directory
source set-os-env.sh                     Set OS environment variables per your app/.env file                
./set-azd-env.sh agents/epl              Set azd `epl` environment variables per your app/.env file  

cd agents/epl                            Navigate to the agent directory

./copy-master-src.sh                     Get the latest reusable python modules from app/src/

azd ai agent run epl --environment epl   Run the Python agent locally
                                         Visit the Foundry Toolkit with your browser at http://127.0.0.1:8087/

./deploy.sh                              Build the Docker container and deploy to Foundry.
                                         Ensure that Docker Desktop is running on your workstation/laptop.

azd ai agent show epl                    Display the deployment details and version

azd ai agent monitor --follow            Stream the logs to your terminal.  CTRL-C to stop.


azd ai agent invoke epl 'where is arsenal?' --environment epl       Invoke the deployed agent

Output:
Agent:        epl (remote)
Message:      "where is arsenal?"
Session:      (new -- server will assign)
Conversation: conv_004adf43c0b7408200qhyDQHWlQ0IjzP5H2oyTOdO1RKVijoQq

Session:      8799b6e540f74caea3ca4703587f9e6663b6ec1d2c2cfbeb21c070c00cd349e (assigned by server)
Trace ID:     72f509b390b28b8acd8c823d3bc5d7b9
Response:     caresp_004adf43c0b7408200ZiEKF44XgmAwfKkGkohvbWJi0o7cmIXl
[epl] Arsenal Football Club is based in London. Their home ground is Emirates Stadium, which has a capacity of 60,704. The club's official address is Highbury House, 75 Drayton Park, London, N5 1BU. The CEO is Richard Garlick, and the first team manager is Mikel Arteta. Their kit manufacturer is adidas and the shirt sponsor is Emirates  .


azd ai agent invoke epl 'who plays goalkeeper for arsenal?' --environment epl

Agent:        epl (remote)
Message:      "who plays goalkeeper for arsenal?"
Session:      8799b6e540f74caea3ca4703587f9e6663b6ec1d2c2cfbeb21c070c00cd349e
Conversation: conv_004adf43c0b7408200qhyDQHWlQ0IjzP5H2oyTOdO1RKVijoQq

Trace ID:     7ffec3a1960d8bbb010d3189d2f88ad3
Response:     caresp_004adf43c0b7408200VrFIDTug10stjsWBpg6Kcdd77nLPgQt2
[epl] The main goalkeeper for Arsenal in the 2025/26 season is David Raya, who played 37 matches without being substituted. Additionally, Kepa Arrizabalaga appeared in 37 matches mostly as a substitute (1 start, 0 subs). Another goalkeeper listed is Andre Harriman-Annous but with very limited appearances (2 matches).


azd ai agent invoke epl 'Are there any games scheduled in London on April 24?' --environment epl

Agent:        epl (remote)
Message:      "Are there any games scheduled in London on April 24?"
Session:      8799b6e540f74caea3ca4703587f9e6663b6ec1d2c2cfbeb21c070c00cd349e
Conversation: conv_004adf43c0b7408200qhyDQHWlQ0IjzP5H2oyTOdO1RKVijoQq

Trace ID:     ca62e77ab03ad3b5e3658ae9382c14e1
Response:     caresp_004adf43c0b7408200HMkgek2qfpP5uYw10oLdLnDuWgBTZmIg
[epl] On April 24, 2027, there are several Premier League matches scheduled in London:

- Chelsea vs Manchester City (at Chelsea's stadium, London)
- Everton vs Brighton & Hove Albion (at Everton's stadium, Liverpool, not London)
- Tottenham Hotspur vs Hull City (at Tottenham Hotspur's stadium, London)

So, the matches in London on April 24 are Chelsea vs Manchester City and Tottenham Hotspur vs Hull City.

No Arsenal match is scheduled in London on that date; Arsenal plays away against A.F.C. Bournemouth on April 24, 2027 .
```
