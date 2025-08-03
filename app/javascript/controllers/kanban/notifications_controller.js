import { Controller } from "@hotwired/stimulus"
import { FetchRequest } from "@rails/request.js"

export default class extends Controller {
  static values = { subscriptionsUrl: String }
  static targets = ["subscribeButton", "notAllowedNotice"]

async subscribe(event) {
  event.preventDefault()
  console.log("[NotificationBell] Subscribe clicked")

  try {
    if (!("Notification" in window)) throw new Error("Notifications not supported")
    if (!("serviceWorker" in navigator)) throw new Error("Service Worker not supported")

    console.log("[NotificationBell] Requesting notification permission…")
    const permission = await Notification.requestPermission()
    console.log(`[NotificationBell] Notification permission: ${permission}`)

    if (permission !== "granted") {
      this.showNotAllowedDialog()
      return
    }

    console.log("[NotificationBell] Getting VAPID key…")
    const vapidKey = this.getVapidKey()

    console.log("[NotificationBell] Getting Service Worker registration…")
    const registration = await this.getServiceWorkerRegistration()

    console.log("[NotificationBell] Checking for existing push subscription…")
    const existing = await registration.pushManager.getSubscription()

    const subscription = existing || await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: vapidKey
    })

    console.log("[NotificationBell] Subscription object ready:", subscription.endpoint)

    await this.syncSubscription(subscription)

    console.log("[NotificationBell] Subscription complete ✅")

  } catch (err) {
    console.error("[NotificationBell] Error in subscribe:", err)
    this.showNotAllowedDialog()
  }
}

#apiPayload(subscription) {
  const json = subscription.toJSON()
  const { endpoint } = json
  const p256dh = json.keys?.p256dh || ""
  const auth = json.keys?.auth || ""

  return JSON.stringify({
    push_subscription: {
      endpoint,
      p256dh: p256dh,
      auth: auth
    }
  })
}

  showNotAllowedDialog() {
    const dialog = this.notAllowedNoticeTarget
    console.log("[NotificationBell] Showing 'Not Allowed' dialog")
    if (dialog?.showModal) dialog.showModal()
    else alert("Notifications aren't allowed.")
  }

  getVapidKey() {
    const meta = document.querySelector("meta[name='vapid-public-key']")
    if (!meta?.content) {
      throw new Error("[NotificationBell] VAPID public key not found in meta tag")
    }

    console.log("[NotificationBell] Converting VAPID public key to Uint8Array")
    return this.base64ToUint8Array(meta.content)
  }

  async getServiceWorkerRegistration() {
  console.log("[NotificationBell] Waiting for Service Worker to be ready…")

  let registration = await navigator.serviceWorker.getRegistration()
  if (!registration) {
    console.log("[NotificationBell] No Service Worker found — registering…")
    registration = await navigator.serviceWorker.register("/service-worker")
  }

  if (!registration) {
    throw new Error("[NotificationBell] Failed to register Service Worker")
  }

  console.log("[NotificationBell] Service Worker is ready:", registration)

  return registration
  }

  async syncSubscription(subscription) {
    const data = this.#apiPayload(subscription)
    console.log("[NotificationBell] Posting subscription to:", this.subscriptionsUrlValue)
    console.log("[NotificationBell] Payload:", data)

    const request = new FetchRequest("post", this.subscriptionsUrlValue, {
      body: data,
      contentType: "application/json",
      responseKind: "json"
    })

    const response = await request.perform()
    console.log("[NotificationBell] Server response:", response.status, response.ok)

    if (!response.ok) {
      console.warn("[NotificationBell] Sync failed — unsubscribing from push")
      await subscription.unsubscribe()
    }
  }

  base64ToUint8Array(base64) {
    const padding = "=".repeat((4 - base64.length % 4) % 4)
    const base64Str = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/")
    const raw = atob(base64Str)
    const buffer = new Uint8Array(raw.length)

    for (let i = 0; i < raw.length; ++i) {
      buffer[i] = raw.charCodeAt(i)
    }

    console.log("[NotificationBell] Converted VAPID key to Uint8Array")
    return buffer
  }
}
