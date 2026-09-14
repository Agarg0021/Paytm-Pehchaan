import Soundbox from "../components/Soundbox.jsx";

export default function Counter({ merchant, event, onAdvance }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 pb-16 pt-10">
      <header className="mb-10 flex items-end justify-between">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-ink/45">
            Paytm Pehchaan
          </p>
          <h1 className="deva mt-1 text-3xl font-semibold tracking-tight">
            {merchant?.name ?? "Verma Kirana Store"}
          </h1>
          <p className="text-sm text-ink/55">
            {merchant ? `${merchant.locality}, ${merchant.city}` : "Laxmi Nagar, Delhi"}
          </p>
        </div>
        <p className="max-w-[240px] text-right text-[12px] leading-relaxed text-ink/45">
          Screen for the shopkeeper.
          <br />
          Speaker for the room.
        </p>
      </header>

      <div className="flex flex-1 flex-col items-center justify-center">
        <Soundbox event={event} onAdvance={onAdvance} />
        <div
          className="wood -mt-1 h-[14px] w-[420px] rounded-[2px] sm:w-[460px]"
          style={{ boxShadow: "0 10px 24px rgba(40,28,12,0.28)" }}
        />
        <div className="h-[7px] w-[560px] max-w-[92vw] rounded-b-sm bg-[#5c3a22]/70" />
        <p className="mt-8 text-center text-[12px] text-ink/40">
          Click the device or press space — a payment lands, the amount is spoken, the cue is not.
        </p>
      </div>
    </div>
  );
}
