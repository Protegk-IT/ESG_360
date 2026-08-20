import { CheckCircle2 } from "lucide-react";

export default function SurveyThankYou() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4">
      <div className="flex flex-col items-center text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
          <CheckCircle2 className="h-8 w-8" />
        </div>

        <h1 className="mt-6 text-2xl font-semibold text-[#22243A]">Thank you</h1>

        <p className="mt-2 max-w-xs text-sm leading-6 text-slate-500">
          Your response has been recorded.
        </p>
      </div>
    </div>
  );
}