import {
  useParams,
} from "react-router-dom";

import {
  CheckCircle2,
  FileText,
} from "lucide-react";

import {
  Card,
  CardContent,
} from "@/components/ui/card";

import {
  Button,
} from "@/components/ui/button";

import {
  Separator,
} from "@/components/ui/separator";

export default function SurveyThankYou() {
  const { token } = useParams<{
    token: string;
  }>();

  return (
    <div
      className="
        min-h-screen
        bg-slate-50
      "
    >
      {/* ==================================================
          TOP HEADER
      ================================================== */}

      <header
        className="
          border-b
          border-slate-200
          bg-white
        "
      >
        <div
          className="
            mx-auto
            flex
            w-full
            max-w-3xl
            items-center
            gap-3
            px-4
            py-3
            sm:px-6
          "
        >
          <div
            className="
              flex
              h-9
              w-9
              shrink-0
              items-center
              justify-center
              rounded-lg
              bg-[#F1EFFF]
              text-[#4A3FD6]
            "
          >
            <FileText className="h-4 w-4" />
          </div>

          <p
            className="
              truncate
              text-sm
              font-semibold
              text-[#22243A]
            "
          >
            Materiality Survey
          </p>
        </div>
      </header>

      {/* ==================================================
          CONTENT
      ================================================== */}

      <main
        className="
          flex
          min-h-[calc(100vh-57px)]
          items-center
          justify-center
          px-4
          py-8
          sm:px-6
        "
      >
        <Card
          className="
            w-full
            max-w-lg
            overflow-hidden
            border-slate-200
            bg-white
            shadow-sm
          "
        >
          {/* ESG top accent */}
          <div
            className="
              h-2
              bg-[#4A3FD6]
            "
          />

          <CardContent
            className="
              px-5
              py-10
              text-center
              sm:px-8
              sm:py-12
            "
          >
            {/* Success icon */}
            <div
              className="
                mx-auto
                flex
                h-16
                w-16
                items-center
                justify-center
                rounded-full
                bg-emerald-50
                text-emerald-600
                sm:h-20
                sm:w-20
              "
            >
              <CheckCircle2
                className="
                  h-9
                  w-9
                  sm:h-10
                  sm:w-10
                "
              />
            </div>

            {/* Heading */}
            <h1
              className="
                mt-6
                text-2xl
                font-semibold
                tracking-tight
                text-[#22243A]
                sm:text-3xl
              "
            >
              Thank you!
            </h1>

            <p
              className="
                mx-auto
                mt-3
                max-w-md
                text-sm
                leading-6
                text-slate-500
                sm:text-base
              "
            >
              Your survey response has been
              submitted successfully.
            </p>

            <Separator className="my-6" />

            {/* Confirmation message */}
            <div
              className="
                rounded-xl
                border
                border-[#DDD8FF]
                bg-[#FBFAFF]
                px-4
                py-4
                text-left
              "
            >
              <p
                className="
                  text-sm
                  font-medium
                  text-[#22243A]
                "
              >
                Your feedback has been recorded.
              </p>

              <p
                className="
                  mt-1
                  text-xs
                  leading-5
                  text-slate-500
                "
              >
                Thank you for taking the time to
                share your perspective. Your input
                will help inform the materiality
                assessment.
              </p>
            </div>

            {/* Token reference - optional, subtle */}
            {token && (
              <p
                className="
                  mt-5
                  break-all
                  text-[10px]
                  leading-4
                  text-slate-400
                "
              >
                Response reference: {token}
              </p>
            )}

            {/* Close / Done */}
            <Button
                type="button"
                disabled
                className="
                    mt-7
                    min-h-[46px]
                    w-full
                    bg-[#4A3FD6]
                    text-white
                "
                >
                Survey Completed
                </Button>

          </CardContent>
        </Card>
      </main>
    </div>
  );
}