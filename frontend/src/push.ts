// Browser notifications: subscribe this device to Web Push.

function vapidKey(): Uint8Array<ArrayBuffer> | null {
  const meta = document.querySelector<HTMLMetaElement>("meta[name='vapid-public-key']")
  if (!meta?.content) return null
  const padding = "=".repeat((4 - (meta.content.length % 4)) % 4)
  const raw = atob((meta.content + padding).replace(/-/g, "+").replace(/_/g, "/"))
  const bytes = new Uint8Array(new ArrayBuffer(raw.length))
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i)
  return bytes
}

function csrfToken(): string {
  const headers = document.body.getAttribute("hx-headers") ?? "{}"
  try {
    return (JSON.parse(headers) as Record<string, string>)["X-CSRFToken"] ?? ""
  } catch {
    return ""
  }
}

async function subscribe(button: HTMLElement): Promise<void> {
  const status = document.getElementById(button.dataset["statusId"] ?? "")
  const say = (text: string): void => {
    if (status) status.textContent = text
  }
  const key = vapidKey()
  if (!("Notification" in window) || !("serviceWorker" in navigator) || !key) {
    say("Notifications aren't available in this browser.")
    return
  }
  const permission = await Notification.requestPermission()
  if (permission !== "granted") {
    say("Notifications aren't allowed. Enable them in your browser settings.")
    return
  }
  const registration = await navigator.serviceWorker.ready
  const subscription =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key }))
  const json = subscription.toJSON()
  const response = await fetch(button.dataset["subscribeUrl"] ?? "", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
    body: JSON.stringify({
      push_subscription: {
        endpoint: json.endpoint,
        p256dh: json.keys?.["p256dh"] ?? "",
        auth: json.keys?.["auth"] ?? "",
      },
    }),
  })
  if (!response.ok) {
    await subscription.unsubscribe()
    say("Couldn't turn on notifications. Please try again.")
    return
  }
  say("Notifications are on for this device.")
}

export function installPush(): void {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch(() => undefined)
  }
  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target.closest<HTMLElement>("[data-push-subscribe]") : null
    if (!target) return
    event.preventDefault()
    void subscribe(target)
  })
}
