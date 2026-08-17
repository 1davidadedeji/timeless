import EventKit
import Foundation

let store = EKEventStore()
let sem = DispatchSemaphore(value: 0)
if #available(macOS 14.0, *) {
    store.requestFullAccessToEvents { _, _ in sem.signal() }
} else {
    store.requestAccess(to: .event) { _, _ in sem.signal() }
}
_ = sem.wait(timeout: .now() + 8)

let iso = ISO8601DateFormatter()
iso.formatOptions = [.withInternetDateTime]

func isJoin(_ s: String) -> Bool {
    let low = s.lowercased()
    return ["zoom.us", "meet.google", "teams.microsoft", "webex.com", "gotomeeting"].contains { low.contains($0) }
}

func pickJoin(url: String?, notes: String?, location: String?) -> String {
    if let url, isJoin(url) { return url }
    let blob = [url, notes, location].compactMap { $0 }.joined(separator: " ")
    guard let re = try? NSRegularExpression(pattern: #"https?://[^\s<>\"]+"#) else { return url ?? "" }
    let ns = blob as NSString
    for m in re.matches(in: blob, range: NSRange(location: 0, length: ns.length)) {
        let u = ns.substring(with: m.range).trimmingCharacters(in: CharacterSet(charactersIn: ").,"))
        if isJoin(u) { return u }
    }
    return ""
}

if CommandLine.arguments.contains("create") {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    guard let obj = try JSONSerialization.jsonObject(with: data) as? [String: String] else {
        fputs("bad json\n", stderr)
        exit(1)
    }
    guard let title = obj["title"],
          let startS = obj["start_at"],
          let endS = obj["end_at"],
          let start = iso.date(from: startS) ?? ISO8601DateFormatter().date(from: startS),
          let end = iso.date(from: endS) ?? ISO8601DateFormatter().date(from: endS),
          let cal = store.defaultCalendarForNewEvents else {
        fputs("missing fields or calendar access\n", stderr)
        exit(1)
    }
    let ev = EKEvent(eventStore: store)
    ev.title = title
    ev.startDate = start
    ev.endDate = end
    ev.calendar = cal
    let join = obj["join_url"] ?? ""
    if !join.isEmpty, let u = URL(string: join) { ev.url = u }
    ev.notes = obj["notes"] ?? join
    do {
        try store.save(ev, span: .thisEvent)
        print(ev.eventIdentifier ?? ev.calendarItemIdentifier)
        exit(0)
    } catch {
        fputs("\(error)\n", stderr)
        exit(1)
    }
}

let start = Date().addingTimeInterval(-3600)
guard let end = Calendar.current.date(byAdding: .day, value: 14, to: Date()) else {
    fputs("[]\n", stdout)
    exit(0)
}
let pred = store.predicateForEvents(withStart: start, end: end, calendars: nil)

var rows: [[String: String]] = []
for ev in store.events(matching: pred) {
    let join = pickJoin(url: ev.url?.absoluteString, notes: ev.notes, location: ev.location)
    rows.append([
        "uid": ev.eventIdentifier ?? ev.calendarItemIdentifier,
        "title": ev.title ?? "Untitled",
        "start_at": iso.string(from: ev.startDate),
        "end_at": iso.string(from: ev.endDate),
        "join_url": join,
        "location": ev.location ?? "",
        "notes": String((ev.notes ?? "").prefix(800)),
    ])
}

let data = try JSONSerialization.data(withJSONObject: rows)
print(String(data: data, encoding: .utf8) ?? "[]")
