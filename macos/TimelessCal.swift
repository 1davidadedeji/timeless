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

let start = Date().addingTimeInterval(-3600)
guard let end = Calendar.current.date(byAdding: .day, value: 14, to: Date()) else {
    fputs("[]\n", stdout)
    exit(0)
}
let pred = store.predicateForEvents(withStart: start, end: end, calendars: nil)
let iso = ISO8601DateFormatter()
iso.formatOptions = [.withInternetDateTime]

var rows: [[String: String]] = []
for ev in store.events(matching: pred) {
    var join = ev.url?.absoluteString ?? ""
    if join.isEmpty, let notes = ev.notes {
        if let match = notes.range(of: #"https?://\S+"#, options: .regularExpression) {
            join = String(notes[match])
        }
    }
    rows.append([
        "uid": ev.eventIdentifier ?? ev.calendarItemIdentifier,
        "title": ev.title ?? "Untitled",
        "start_at": iso.string(from: ev.startDate),
        "end_at": iso.string(from: ev.endDate),
        "join_url": join,
        "location": ev.location ?? "",
        "notes": String((ev.notes ?? "").prefix(500)),
    ])
}

let data = try JSONSerialization.data(withJSONObject: rows)
print(String(data: data, encoding: .utf8) ?? "[]")
