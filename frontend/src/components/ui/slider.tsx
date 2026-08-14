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
  const _values = React.useMemo(
    () =>
      Array.isArray(value)
        ? value
        : Array.isArray(defaultValue)
          ? defaultValue
          : [min, max],
    [value, defaultValue, min, max]
  );

  return (
    <SliderPrimitive.Root
      data-slot="slider"
      defaultValue={defaultValue}
      value={value}
      min={min}
      max={max}
      className={cn(
        "relative flex h-6 w-full touch-none items-center select-none",
        "data-disabled:opacity-50",
        "data-vertical:h-full",
        "data-vertical:min-h-40",
        "data-vertical:w-6",
        "data-vertical:flex-col",
        className
      )}
      {...props}
    >
      {/* TRACK */}
      <SliderPrimitive.Track
        data-slot="slider-track"
        className={cn(
          "relative grow overflow-hidden rounded-full",
          "border border-slate-200",
          "bg-white",
          "data-horizontal:h-2",
          "data-horizontal:w-full",
          "data-vertical:h-full",
          "data-vertical:w-2"
        )}
      >
        {/* FILLED / PROGRESS PART */}
        <SliderPrimitive.Range
          data-slot="slider-range"
          className={cn(
            "absolute rounded-full",
            "bg-blue-600",
            "data-horizontal:h-full",
            "data-vertical:w-full"
          )}
        />
      </SliderPrimitive.Track>

      {/* THUMB */}
      {Array.from(
        { length: _values.length },
        (_, index) => (
          <SliderPrimitive.Thumb
            data-slot="slider-thumb"
            key={index}
            className={cn(
              "relative block size-7 shrink-0",
              "rounded-full",

              // White center
              "bg-white",

              // Colored outline
              "border-2 border-blue-400",

              // Very subtle shadow
              "shadow-sm",

              // Smooth interaction
              "transition-transform duration-150",

              // Hover
              "hover:scale-105",

              // Focus
              "focus-visible:outline-none",
              "focus-visible:ring-2",
              "focus-visible:ring-blue-200",

              // Active
              "active:scale-100",

              // Disabled
              "disabled:pointer-events-none",
              "disabled:opacity-50"
            )}
          />
        )
      )}
    </SliderPrimitive.Root>
  );
}

export { Slider };