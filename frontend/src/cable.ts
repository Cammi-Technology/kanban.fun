// WebSocket broadcasts through the htmx ws extension.
//
// The server prefixes every message with <!--cable:ID-->. IDs increase
// monotonically across all topics, so we drop anything we've already applied
// (duplicate protection) and, after a reconnect, ask the server to replay
// what we missed ("resume").

const FRAME = /^<!--cable:(\d+)-->/

let lastEventId = 0

interface WsMessageDetail {
  message: string
}

interface WsOpenDetail {
  socketWrapper: { send(message: string, source?: Element): void }
}

export function eventIdOf(message: string): number | null {
  const match = FRAME.exec(message)
  return match?.[1] ? Number(match[1]) : null
}

export function installCable(): void {
  document.body.addEventListener("htmx:wsBeforeMessage", (event) => {
    const detail = (event as CustomEvent<WsMessageDetail>).detail
    const id = eventIdOf(detail.message)
    if (id === null) return
    if (id <= lastEventId) {
      event.preventDefault() // already applied
      return
    }
    lastEventId = id
    document.body.dataset["cableLastEventId"] = String(id)
  })

  document.body.addEventListener("htmx:wsOpen", (event) => {
    const detail = (event as CustomEvent<WsOpenDetail>).detail
    document.body.dataset["cableConnected"] = "true"
    if (lastEventId > 0) {
      detail.socketWrapper.send(JSON.stringify({ type: "resume", last_event_id: lastEventId }))
    }
  })

  document.body.addEventListener("htmx:wsClose", () => {
    document.body.dataset["cableConnected"] = "false"
  })
}
