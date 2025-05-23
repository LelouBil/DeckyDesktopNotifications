import {ButtonItem, PanelSection, PanelSectionRow, staticClasses} from "@decky/ui";
import {addEventListener, callable, definePlugin, removeEventListener, toaster, ToastNotification,} from "@decky/api"
import {FaBell} from "react-icons/fa";
import {useEffect, useState} from "react";


const start_server = callable("start_server");
const stop_server = callable("stop_server");
// const get_server_state = callable<[],boolean>("get_server_state");
const on_notification_click = callable<[id: number, action: string], void>("notification_click");

function Content() {

    const [started, setStarted] = useState(false);

    useEffect(() => {
        let started_listener = addEventListener<[boolean]>("server_state",(started) => {
            setStarted(started)
        })
        return () => {
            removeEventListener("server_state", started_listener);
        }
    })

    return (
        <PanelSection title="Panel Section">
            <PanelSectionRow>
                <p>State: {started ? "Started" : "Stopped"}</p>
                {started ?
                    (
                        <ButtonItem onClick={async () => await stop_server()}>Stop</ButtonItem>
                    ) :
                    (
                        <ButtonItem onClick={async () => await start_server()}>Start</ButtonItem>
                    )
                }
            </PanelSectionRow>
            <PanelSectionRow>
            </PanelSectionRow>

            {/* <PanelSectionRow>
        <div style={{ display: "flex", justifyContent: "center" }}>
          <img src={logo} />
        </div>
      </PanelSectionRow> */}

            {/*<PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={() => {
            Navigation.Navigate("/decky-plugin-test");
            Navigation.CloseSideMenus();
          }}
        >
          Router
        </ButtonItem>
      </PanelSectionRow>*/}
        </PanelSection>
    );
};


export default definePlugin(() => {
    console.log("Template plugin initializing, this is called once on frontend startup")

    let notif_map = new Map<number, ToastNotification>()
    addEventListener<
        [
            app_name: string,
            id: number,
            app_icon: string,
            summary: string,
            body: string,
            on_click: string,
            expire_timeout: number
        ]
    >("show_notification", (app_name, id, app_icon, _summary, body,
                            on_click, expire_timeout) => {
        let icon_src = undefined;
        if (app_icon) {
            let splat = app_icon.split(",")
            if (splat[0] == "b64") {
                icon_src = "data:image/png;" + splat[1]
            }
            if (splat[0] == "path") {
                icon_src = splat[1]
            }
        }
        let t = toaster.toast({
            title: app_name ? `${app_name} - ${_summary}` : _summary,
            body: body ? body : undefined,
            icon: icon_src ? <img alt={app_name} src={icon_src}/> : null,
            duration: expire_timeout == 0 ? 9999999999 : expire_timeout == -1 ? undefined : expire_timeout,
            showToast: true,
            onClick: () => {
                on_notification_click(id, on_click).catch((e) => {
                    console.error(e)
                })
                notif_map.delete(id);
            }
        })
        notif_map.set(id, t);
    });

    addEventListener<[id: number]>("close_notification", (id: number) => {
        if (notif_map.has(id)) {
            let t = notif_map.get(id)!
            notif_map.delete(id)
            t.dismiss();
            return true;
        } else return false;
    });



    return {
        // The name shown in various decky menus
        name: "Decky Desktop Notifications",
        // The element displayed at the top of your plugin's menu
        titleView: <div className={staticClasses.Title}>Decky Desktop Notifications</div>,
        // The content of your plugin's menu
        content: <Content/>,
        // The icon displayed in the plugin list
        icon: <FaBell/>,
        // The function triggered when your plugin unloads
        onDismount() {
            console.log("Unloading")
        },
    };
});
