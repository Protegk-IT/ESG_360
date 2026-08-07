"use client";

import * as React from "react";
import { Select as SelectPrimitive } from "radix-ui";

import {
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

/* ===========================================================
   ROOT
=========================================================== */

function Select(
  props: React.ComponentProps<typeof SelectPrimitive.Root>
) {
  return (
    <SelectPrimitive.Root
      data-slot="select"
      {...props}
    />
  );
}

/* ===========================================================
   GROUP
=========================================================== */

function SelectGroup({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Group>) {
  return (
    <SelectPrimitive.Group
      data-slot="select-group"
      className={cn(
        "py-1",
        className
      )}
      {...props}
    />
  );
}

/* ===========================================================
   VALUE
=========================================================== */

function SelectValue(
  props: React.ComponentProps<
    typeof SelectPrimitive.Value
  >
) {
  return (
    <SelectPrimitive.Value
      data-slot="select-value"
      {...props}
    />
  );
}

/* ===========================================================
   TRIGGER
=========================================================== */

function SelectTrigger({
  className,
  size = "default",
  children,
  ...props
}: React.ComponentProps<
  typeof SelectPrimitive.Trigger
> & {
  size?: "sm" | "default";
}) {
  return (
    <SelectPrimitive.Trigger
      data-slot="select-trigger"
      data-size={size}
      className={cn(
        `
        flex
        w-full
        items-center
        justify-between

        gap-3

        rounded-md

        border
        border-[#D9DEE8]

        bg-white

        px-3

        shadow-sm

        transition-all
        duration-200
        ease-in-out

        hover:border-[#BFC6D4]

        focus:outline-none
        focus:border-[#4A3FD6]
        focus:ring-2
        focus:ring-[#4A3FD6]/15

        disabled:cursor-not-allowed
        disabled:bg-[#F8F9FC]
        disabled:opacity-60

        data-[placeholder]:text-[#9CA3AF]

        text-sm
        text-[#111827]

        data-[size=default]:h-10
        data-[size=sm]:h-9

        [&>span]:truncate

        [&_svg]:shrink-0
        `,
        className
      )}
      {...props}
    >
      {children}

      <SelectPrimitive.Icon asChild>
        <ChevronDownIcon
          className="
            h-4
            w-4

            text-[#6B7280]

            opacity-80

            transition-transform
            duration-200
          "
        />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
}
/* ===========================================================
   CONTENT
=========================================================== */

function SelectContent({
  className,
  children,
  position = "item-aligned",
  align = "center",
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        data-slot="select-content"
        position={position}
        align={align}
        className={cn(
          `
          z-50

          min-w-[220px]
          overflow-hidden

          rounded-xl

          border
          border-[#D9DEE8]

          bg-white

          p-2

          shadow-xl

          text-sm
          text-[#374151]

          origin-(--radix-select-content-transform-origin)

          transition-all
          duration-200

          data-[state=open]:animate-in
          data-[state=closed]:animate-out

          data-[state=open]:fade-in-0
          data-[state=closed]:fade-out-0

          data-[state=open]:zoom-in-95
          data-[state=closed]:zoom-out-95

          data-[side=bottom]:slide-in-from-top-2
          data-[side=top]:slide-in-from-bottom-2
          data-[side=left]:slide-in-from-right-2
          data-[side=right]:slide-in-from-left-2
          `,
          className
        )}
        {...props}
      >
        <SelectScrollUpButton />

        <SelectPrimitive.Viewport
          data-position={position}
          className={cn(
            `
            p-1

            data-[position=popper]:w-full
            data-[position=popper]:min-w-[var(--radix-select-trigger-width)]
            `
          )}
        >
          {children}
        </SelectPrimitive.Viewport>

        <SelectScrollDownButton />
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}

/* ===========================================================
   LABEL
=========================================================== */

function SelectLabel({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Label>) {
  return (
    <SelectPrimitive.Label
      data-slot="select-label"
      className={cn(
        `
        px-3
        py-2

        text-xs

        font-semibold

        uppercase

        tracking-wide

        text-[#6B7280]
        `,
        className
      )}
      {...props}
    />
  );
}

/* ===========================================================
   ITEM
=========================================================== */

function SelectItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      data-slot="select-item"
      className={cn(
        `
        relative

        flex
        w-full
        items-center

        gap-3

        rounded-lg

        px-3
        py-2.5

        text-sm
        font-medium

        text-[#374151]

        cursor-pointer

        outline-none

        transition-all
        duration-200

        hover:bg-[#EEF0FF]
        hover:text-[#4A3FD6]

        focus:bg-[#EEF0FF]
        focus:text-[#4A3FD6]

        data-[state=checked]:bg-[#EEF0FF]
        data-[state=checked]:text-[#4A3FD6]

        data-disabled:pointer-events-none
        data-disabled:opacity-50
        `
      ,
        className
      )}
      {...props}
    >
      <span
        className="
          absolute
          right-3

          flex
          items-center
          justify-center
        "
      >
        <SelectPrimitive.ItemIndicator>
          <CheckIcon
            className="
              h-3.5
              w-3.5

              text-[#4A3FD6]
            "
          />
        </SelectPrimitive.ItemIndicator>
      </span>

      <SelectPrimitive.ItemText>
        {children}
      </SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  );
}

/* ===========================================================
   SEPARATOR
=========================================================== */

function SelectSeparator({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Separator>) {
  return (
    <SelectPrimitive.Separator
      data-slot="select-separator"
      className={cn(
        `
        my-2

        h-px

        bg-[#ECEEF5]
        `,
        className
      )}
      {...props}
    />
  );
}
/* ===========================================================
   SCROLL UP BUTTON
=========================================================== */

function SelectScrollUpButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollUpButton>) {
  return (
    <SelectPrimitive.ScrollUpButton
      data-slot="select-scroll-up-button"
      className={cn(
        `
        flex
        items-center
        justify-center

        py-2

        bg-white

        text-[#6B7280]

        transition-colors
        duration-200

        hover:bg-[#F8F9FC]
        `,
        className
      )}
      {...props}
    >
      <ChevronUpIcon
        className="
          h-3.5
          w-3.5
        "
      />
    </SelectPrimitive.ScrollUpButton>
  );
}

/* ===========================================================
   SCROLL DOWN BUTTON
=========================================================== */

function SelectScrollDownButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollDownButton>) {
  return (
    <SelectPrimitive.ScrollDownButton
      data-slot="select-scroll-down-button"
      className={cn(
        `
        flex
        items-center
        justify-center

        py-2

        bg-white

        text-[#6B7280]

        transition-colors
        duration-200

        hover:bg-[#F8F9FC]
        `,
        className
      )}
      {...props}
    >
      <ChevronDownIcon
        className="
          h-3.5
          w-3.5
        "
      />
    </SelectPrimitive.ScrollDownButton>
  );
}

/* ===========================================================
   EXPORTS
=========================================================== */

export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectScrollDownButton,
  SelectScrollUpButton,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
};