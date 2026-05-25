"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface RadioGroupContextValue {
  value?: string;
  onValueChange?: (value: string) => void;
  name?: string;
}

const RadioGroupContext = React.createContext<RadioGroupContextValue | undefined>(
  undefined
);

interface RadioGroupProps {
  value?: string;
  onValueChange?: (value: string) => void;
  name?: string;
  children: React.ReactNode;
  className?: string;
}

const RadioGroup = ({ value, onValueChange, name, children, className }: RadioGroupProps) => {
  return (
    <RadioGroupContext.Provider value={{ value, onValueChange, name }}>
      <div className={cn("space-y-2", className)}>{children}</div>
    </RadioGroupContext.Provider>
  );
};

interface RadioGroupItemProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  value: string;
}

const RadioGroupItem = React.forwardRef<HTMLInputElement, RadioGroupItemProps>(
  ({ className, value: itemValue, ...props }, ref) => {
    const context = React.useContext(RadioGroupContext);
    if (!context) throw new Error("RadioGroupItem must be used within RadioGroup");

    const isChecked = context.value === itemValue;

    return (
      <label className="inline-flex items-center cursor-pointer">
        <input
          type="radio"
          ref={ref}
          className="sr-only"
          value={itemValue}
          checked={isChecked}
          onChange={() => context.onValueChange?.(itemValue)}
          name={context.name}
          {...props}
        />
        <div
          className={cn(
            "h-5 w-5 rounded-full border-2 border-divider flex items-center justify-center transition-colors focus-ring",
            isChecked && "border-primary",
            className
          )}
        >
          {isChecked && (
            <div className="h-2.5 w-2.5 rounded-full bg-primary" />
          )}
        </div>
      </label>
    );
  }
);
RadioGroupItem.displayName = "RadioGroupItem";

export { RadioGroup, RadioGroupItem };
