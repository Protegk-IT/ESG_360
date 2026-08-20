import * as React from "react";
import { Slider as SliderPrimitive } from "radix-ui";

import { cn } from "@/lib/utils";

function Slider({
  className,
  defaultValue,
  value,
  min = 0,
  max = 100,
  ...props
}: React.ComponentProps<typeof SliderPrimitive.Root>) {
  const values = React.useMemo(
    () =>
      Array.isArray(value)
        ? value
        : Array.isArray(defaultValue)
          ? defaultValue
          : [min],
    [value, defaultValue, min]
  );

  const currentValue =
    typeof values[0] === "number" ? values[0] : min;

  const percentage =
    max > min
      ? ((currentValue - min) / (max - min)) * 100
      : 0;

  return (
    <SliderPrimitive.Root
      data-slot="slider"
      defaultValue={defaultValue}
      value={value}
      min={min}
      max={max}
      className={cn(
        "relative flex w-full touch-none select-none items-center",
        "h-8",
        "data-[disabled]:opacity-50",
        className
      )}
      {...props}
    >
      {/* =====================================================
          TRACK
      ===================================================== */}
      <SliderPrimitive.Track
        data-slot="slider-track"
        className={cn(
          "relative w-full grow overflow-hidden rounded-full",
          "bg-[#f1f1f4]",
          "border border-[#e8e8ec]",
          "h-[10px]"
        )}
      >
        {/* ===================================================
            FILLED AREA
        =================================================== */}
        <SliderPrimitive.Range
          data-slot="slider-range"
          className="absolute h-full rounded-full bg-[#5b5bd6]"
          style={{
            width: `${percentage}%`,
          }}
        />
      </SliderPrimitive.Track>

      {/* =====================================================
          THUMB
      ===================================================== */}
      {values.map((_, index) => (
        <SliderPrimitive.Thumb
          data-slot="slider-thumb"
          key={index}
          className={cn(
            "absolute block",
            "h-[22px] w-[22px]",
            "top-1/2",
        "-translate-y-1/2",

            // white center
            "rounded-full",
            "bg-white",

            // teal outline
            "border-[3px]",
            "border-[#5b5bd6]",

            // subtle shadow
            "shadow-[0_1px_4px_rgba(0,0,0,0.08)]",

            // smooth movement
            "transition-transform",
            "duration-150",
            "ease-out",

            // hover
            "hover:scale-[1.04]",

            // focus
            "focus-visible:outline-none",
            "focus-visible:ring-2",
            "focus-visible:ring-[#55d8c6]/30",
            "focus-visible:ring-offset-2",

            // active
            "active:scale-100",

            // disabled
            "disabled:pointer-events-none",
            "disabled:opacity-50"
          )}
          style={{
            left: `${percentage}%`,
          }}
        />
      ))}
    </SliderPrimitive.Root>
  );
}

export { Slider };