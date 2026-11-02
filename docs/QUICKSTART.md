# NetSpout PulseForge: your first run

You need PulseForge installed ([INSTALL](INSTALL.md)) and a Splunk HEC token plus an index you may write to. Use a **test index**, not a production one.

1. **Open PulseForge.** Splunk Web → *Apps* → *NetSpout PulseForge*. The first time, open **PulseForge Onboarding** and enter your HEC URL and token, the search endpoint and credentials, and the indexes PulseForge may use. Run the connection test: you want *reachable*, *authenticated*, *accepted* and *indexing verified*.
2. **Select a scenario.** Open **Use Case Explorer**, search or filter, and pick one. A good first choice is the NetFlow scenario `NF-NOC-01-ELEPHANT` (see [SCENARIOS](SCENARIOS.md) for the full list).
3. **Preview it.** Choose **Preview** to see the phases and the sourcetypes it will produce. Nothing is sent yet.
4. **Choose the destination.** PulseForge only sends to the destination and indexes you authorized in step 1. Pick the test index.
5. **Start a bounded run.** Choose **Run scenario** (or **Start Streaming** for a single sourcetype). Keep the event rate low. *Accepted* means HEC took the events.
6. **Confirm indexed events.** Choose **Verify in Splunk**. PulseForge runs a separate Splunk search for this run and reports how many events are really indexed; indexed can trail accepted by a few seconds. You can also search yourself:
   ```
   index=<your test index> netspout_run_id=<run id>
   ```
7. **Open the dashboard.** Choose **Open dashboard** on the run, or open `pf_<scenario id>` from the app's dashboard menu.

**Stop** ends a run at any time; an interrupted run is never resumed or resent automatically. If something fails: [Troubleshooting](TROUBLESHOOTING.md).
