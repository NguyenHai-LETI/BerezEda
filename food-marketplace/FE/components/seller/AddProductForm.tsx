"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LockerUnitSelector } from "@/components/seller/LockerUnitSelector";
import { LockerSelectionModal } from "@/components/seller/LockerSelectionModal";
import { RegistrationConfirmationPage } from "@/components/seller/RegistrationConfirmationPage";
import { RegistrationCompletionModal } from "@/components/seller/RegistrationCompletionModal";
import { lockers, getLockerById, getLockerUnitsByLockerIdAll, getLockerUnitById } from "@/lib/seller-mock";
import { sellerRoutes } from "@/lib/seller-routes";
import { cn } from "@/lib/utils";

const productSchema = z.object({
  title: z.string().min(1, "Title is required").max(65, "Title is too long"),
  description: z.string().min(10, "Description must be at least 10 characters").max(500, "Description is too long"),
  price: z.number().min(1, "Price must be greater than 0"),
  stockQuantity: z.number().min(0, "Stock quantity cannot be negative").int(),
  lockerId: z.string().min(1, "Please select a locker"),
  lockerUnitId: z.string().min(1, "Please select a locker unit"),
  imageUrl: z.string().url("Please enter a valid image URL").optional().or(z.literal("")),
  donationMode: z.boolean().default(false),
  discountRate: z.number().min(0).max(100).optional(),
  salesDurationHours: z.number().min(1).default(3),
});

type ProductFormData = z.infer<typeof productSchema>;

interface AddProductFormProps {
  onSubmit?: (data: ProductFormData) => void | Promise<void>;
  initialData?: Partial<ProductFormData>;
}

export function AddProductForm({ onSubmit, initialData }: AddProductFormProps) {
  const router = useRouter();
  const [step, setStep] = useState<"select-locker" | "product-info">("select-locker");
  const [selectedLockerId, setSelectedLockerId] = useState<string>(
    initialData?.lockerId || lockers[0]?.id || ""
  );
  const [selectedLockerUnitId, setSelectedLockerUnitId] = useState<string>(
    initialData?.lockerUnitId || ""
  );
  const [donationMode, setDonationMode] = useState(false);
  const [discountRate, setDiscountRate] = useState<number | undefined>(50);
  const [salesDurationHours, setSalesDurationHours] = useState(3);
  const [showLockerConfirmModal, setShowLockerConfirmModal] = useState(false);
  const [showConfirmationPage, setShowConfirmationPage] = useState(false);
  const [showCompletionModal, setShowCompletionModal] = useState(false);
  const [submittedData, setSubmittedData] = useState<ProductFormData | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setValue,
    watch,
  } = useForm<ProductFormData>({
    resolver: zodResolver(productSchema),
    defaultValues: {
      title: initialData?.title || "",
      description: initialData?.description || "",
      price: initialData?.price || 0,
      stockQuantity: initialData?.stockQuantity || 0,
      lockerId: initialData?.lockerId || "",
      lockerUnitId: initialData?.lockerUnitId || "",
      imageUrl: initialData?.imageUrl || "",
      donationMode: false,
      discountRate: 50,
      salesDurationHours: 3,
    },
  });

  const selectedLocker = selectedLockerId ? getLockerById(selectedLockerId) : undefined;
  const selectedLockerUnit = selectedLockerUnitId ? getLockerUnitById(selectedLockerUnitId) : undefined;
  const allUnits = selectedLockerId ? getLockerUnitsByLockerIdAll(selectedLockerId) : [];
  const imageUrl = watch("imageUrl");

  // Calculate prices with discount
  const basePrice = watch("price") || 0;
  const finalPrice = discountRate && donationMode
    ? Math.floor(basePrice * (1 - discountRate / 100))
    : basePrice;

  const handleLockerChange = (lockerId: string) => {
    setSelectedLockerId(lockerId);
    setSelectedLockerUnitId(""); // Reset unit selection when locker changes
    setValue("lockerId", lockerId);
    setValue("lockerUnitId", "");
  };

  const handleUnitSelect = (unitId: string) => {
    setSelectedLockerUnitId(unitId);
    setValue("lockerUnitId", unitId, { shouldValidate: true });
  };

  const handleContinueToProductInfo = () => {
    if (!selectedLockerUnitId || !selectedLockerId) {
      return;
    }
    // Ensure form values are set when moving to product info step
    setValue("lockerId", selectedLockerId, { shouldValidate: true });
    setValue("lockerUnitId", selectedLockerUnitId, { shouldValidate: true });
    setStep("product-info");
  };

  const handleFormSubmit = async (data: ProductFormData) => {
    // Validate locker unit is selected
    if (!selectedLockerUnitId || !selectedLockerId) {
      setValue("lockerUnitId", "", { shouldValidate: true });
      setValue("lockerId", "", { shouldValidate: true });
      return;
    }

    // Ensure lockerId and lockerUnitId are in the data
    const fullData: ProductFormData = {
      ...data,
      lockerId: selectedLockerId,
      lockerUnitId: selectedLockerUnitId,
      donationMode,
      discountRate,
      salesDurationHours,
    };

    setSubmittedData(fullData);
    setShowLockerConfirmModal(true);
  };

  const handleConfirmLockerSelection = async () => {
    if (!submittedData || !selectedLocker || !selectedLockerUnit) return;

    setShowLockerConfirmModal(false);
    // Show confirmation page with checkboxes
    setShowConfirmationPage(true);
  };

  const handleConfirmRegistration = async () => {
    if (!submittedData || !selectedLocker || !selectedLockerUnit) return;

    setShowConfirmationPage(false);
    
    // In real app, this would call an API
    await onSubmit?.(submittedData);
    
    // Show completion modal with QR code
    setShowCompletionModal(true);
  };

  const handleConfirmDeposit = () => {
    // Close modal first
    setShowCompletionModal(false);
    // Use setTimeout to ensure modal closes before navigation
    setTimeout(() => {
      router.push(sellerRoutes.home);
    }, 100);
  };

  // Generate product code
  const productCode = submittedData
    ? `COMBO_${Date.now()}`
    : "";

  // If showing confirmation page, render it instead of form
  if (showConfirmationPage && selectedLocker && selectedLockerUnit) {
    return (
      <RegistrationConfirmationPage
        locker={selectedLocker as any}
        lockerUnit={selectedLockerUnit}
        depositDeadlineSeconds={1200}
        onConfirm={handleConfirmRegistration}
        onCancel={() => {
          setShowConfirmationPage(false);
          setSubmittedData(null);
        }}
      />
    );
  }

  // Step 1: Select Locker and Locker Unit
  if (step === "select-locker") {
    return (
      <div className="space-y-6">
        <Card className="p-4 sm:p-6">
          <h2 className="text-lg sm:text-xl font-semibold mb-4">Step 1: Select Locker and Unit</h2>
          
          {/* Locker Dropdown */}
          <div className="mb-6">
            <label htmlFor="locker-select" className="block text-sm font-medium text-text mb-2">
              Select Locker
            </label>
            <select
              id="locker-select"
              value={selectedLockerId}
              onChange={(e) => handleLockerChange(e.target.value)}
              className="w-full px-3 py-2 border border-divider rounded-md focus-ring"
            >
              {lockers.map((locker) => (
                <option key={locker.id} value={locker.id}>
                  {locker.name} - {locker.areaDescription}
                </option>
              ))}
            </select>
          </div>

          {/* Locker Unit Selector */}
          {selectedLocker && (
            <LockerUnitSelector
              lockerId={selectedLocker.id}
              lockerName={selectedLocker.name}
              units={allUnits}
              selectedUnitId={selectedLockerUnitId}
              onSelectUnit={handleUnitSelect}
            />
          )}

          {/* Continue Button */}
          <div className="mt-6 flex gap-3">
            <Button
              variant="secondary"
              onClick={() => router.back()}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleContinueToProductInfo}
              disabled={!selectedLockerUnitId}
              className="flex-1"
            >
              Continue to Product Info
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // Step 2: Product Information Form
  return (
    <>
      <div className="space-y-6">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => setStep("select-locker")}
          className="mb-4"
        >
          ← Back to Locker Selection
        </Button>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
          {/* Hidden fields for locker selection */}
          <input type="hidden" {...register("lockerId")} value={selectedLockerId} />
          <input type="hidden" {...register("lockerUnitId")} value={selectedLockerUnitId} />
          
          {/* Product Information */}
          <Card className="p-4 sm:p-6">
            <h2 className="text-lg sm:text-xl font-semibold mb-4">Step 2: Product Information</h2>
            <div className="space-y-4">
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-text mb-1">
                  Product Name (Required)
                </label>
                <input
                  id="title"
                  type="text"
                  {...register("title")}
                  className="w-full px-3 py-2 border border-divider rounded-md focus-ring"
                  placeholder="Enter product title"
                  maxLength={65}
                />
                <div className="flex justify-between items-center mt-1">
                  {errors.title ? (
                    <p className="text-xs text-danger">{errors.title.message}</p>
                  ) : (
                    <span></span>
                  )}
                  <p className="text-xs text-muted">{watch("title")?.length || 0}/65</p>
                </div>
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-text mb-1">
                  Product Description (Required)
                </label>
                <textarea
                  id="description"
                  {...register("description")}
                  rows={4}
                  className="w-full px-3 py-2 border border-divider rounded-md focus-ring resize-none"
                  placeholder="Enter product description"
                  maxLength={500}
                />
                <div className="flex justify-between items-center mt-1">
                  {errors.description ? (
                    <p className="text-xs text-danger">{errors.description.message}</p>
                  ) : (
                    <span></span>
                  )}
                  <p className="text-xs text-muted">{watch("description")?.length || 0}/500</p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="price" className="block text-sm font-medium text-text mb-1">
                    Selling Price (RUB) *
                  </label>
                  <input
                    id="price"
                    type="number"
                    {...register("price", { valueAsNumber: true })}
                    className="w-full px-3 py-2 border border-divider rounded-md focus-ring"
                    placeholder="0"
                    min="0"
                    step="1"
                  />
                  {errors.price && (
                    <p className="text-xs text-danger mt-1">{errors.price.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="stockQuantity" className="block text-sm font-medium text-text mb-1">
                    Stock Quantity *
                  </label>
                  <input
                    id="stockQuantity"
                    type="number"
                    {...register("stockQuantity", { valueAsNumber: true })}
                    className="w-full px-3 py-2 border border-divider rounded-md focus-ring"
                    placeholder="0"
                    min="0"
                    step="1"
                  />
                  {errors.stockQuantity && (
                    <p className="text-xs text-danger mt-1">{errors.stockQuantity.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label htmlFor="imageUrl" className="block text-sm font-medium text-text mb-1">
                  Package Photo (Product Image)
                </label>
                <input
                  id="imageUrl"
                  type="url"
                  {...register("imageUrl")}
                  className="w-full px-3 py-2 border border-divider rounded-md focus-ring"
                  placeholder="https://example.com/image.jpg"
                />
                {errors.imageUrl && (
                  <p className="text-xs text-danger mt-1">{errors.imageUrl.message}</p>
                )}
                {imageUrl && (
                  <div className="mt-2 relative h-32 w-full rounded-md overflow-hidden bg-divider">
                    <img
                      src={imageUrl}
                      alt="Preview"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Donation Mode & Discount */}
          <Card className="p-4 sm:p-6">
            <div className="space-y-4">
              {/* Donation Mode Toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base sm:text-lg font-semibold mb-1">Apply Donation Mode</h3>
                  <p className="text-xs text-muted">
                    Products will be offered for free during the last 1/3 of the sales time.
                  </p>
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={donationMode}
                    onChange={(e) => setDonationMode(e.target.checked)}
                    className="sr-only"
                  />
                  <div className={cn(
                    "relative w-12 h-6 rounded-full transition-colors",
                    donationMode ? "bg-primary" : "bg-divider"
                  )}>
                    <div className={cn(
                      "absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform",
                      donationMode && "translate-x-6"
                    )} />
                  </div>
                  <span className="text-sm text-muted">Apply</span>
                </label>
              </div>

              {/* Discount Rate Selection */}
              {donationMode && (
                <div>
                  <h3 className="text-base sm:text-lg font-semibold mb-3">Discount Rate Selection</h3>
                  <div className="flex gap-3">
                    {[50, 40, 30].map((rate) => (
                      <label
                        key={rate}
                        className="flex items-center gap-2 cursor-pointer"
                      >
                        <input
                          type="radio"
                          name="discountRate"
                          value={rate}
                          checked={discountRate === rate}
                          onChange={() => setDiscountRate(rate)}
                          className="sr-only"
                        />
                        <div className={cn(
                          "w-5 h-5 rounded-full border-2 flex items-center justify-center",
                          discountRate === rate
                            ? "border-primary"
                            : "border-divider"
                        )}>
                          {discountRate === rate && (
                            <div className="w-2.5 h-2.5 rounded-full bg-primary" />
                          )}
                        </div>
                        <span className="text-sm text-text">{rate}%</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Price Display */}
              <div className="p-4 bg-primary/5 rounded-card space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-muted">Selling Price</span>
                  <span className="text-base font-semibold text-text">
                    ₽{finalPrice.toLocaleString("en-US")}
                  </span>
                </div>
                {donationMode && discountRate && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted">Selected Product Total Price</span>
                      <span className="text-base font-semibold text-text line-through">
                        ₽{basePrice.toLocaleString("en-US")}
                      </span>
                    </div>
                    <div className="flex justify-between pt-2 border-t border-divider">
                      <span className="text-sm text-muted">Food Loss Reduction Amount</span>
                      <span className="text-base font-semibold text-text">
                        {Math.floor(basePrice * 0.1).toLocaleString("en-US")} grams
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted">CO2 Reduction Amount</span>
                      <span className="text-base font-semibold text-text">
                        {(Math.floor(basePrice * 0.1) / 1000).toFixed(2)} kg
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </Card>

          {/* Sales Duration */}
          <Card className="p-4 sm:p-6">
            <h2 className="text-lg sm:text-xl font-semibold mb-4">Sales Duration Settings</h2>
            <div>
              <label htmlFor="salesDuration" className="block text-sm font-medium text-text mb-1">
                Sales End Time
              </label>
              <select
                id="salesDuration"
                value={salesDurationHours}
                onChange={(e) => setSalesDurationHours(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-divider rounded-md focus-ring"
              >
                <option value={1}>1 hour from sales start time</option>
                <option value={2}>2 hours from sales start time</option>
                <option value={3}>3 hours from sales start time</option>
                <option value={6}>6 hours from sales start time</option>
                <option value={12}>12 hours from sales start time</option>
                <option value={24}>24 hours from sales start time</option>
              </select>
              <p className="text-xs text-muted mt-2">
                Sales will start from the moment the item is placed in the reserved box and the door is closed
              </p>
            </div>
          </Card>

          {/* Selected Locker Info */}
          {selectedLocker && selectedLockerUnit && (
            <Card className="p-4 sm:p-6 bg-primary/5">
              <h3 className="text-base font-semibold mb-2">Selected Locker</h3>
              <p className="text-sm text-text">
                <strong>Locker:</strong> {selectedLocker.name}
              </p>
              <p className="text-sm text-text">
                <strong>Unit:</strong> {selectedLockerUnit.unitNumber} ({selectedLockerUnit.temperature}°C) - Box No. {selectedLockerUnit.boxNo}
              </p>
            </Card>
          )}

          {/* Submit Buttons */}
          <div className="flex gap-3 sm:gap-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setStep("select-locker")}
              className="flex-1"
            >
              Back
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? "Registering..." : "Proceed to Preview"}
            </Button>
          </div>
        </form>
      </div>

      {/* Locker Selection Confirmation Modal */}
      {selectedLocker && selectedLockerUnit && (
        <LockerSelectionModal
          open={showLockerConfirmModal}
          onClose={() => {
            setShowLockerConfirmModal(false);
            setSubmittedData(null);
          }}
          onConfirm={handleConfirmLockerSelection}
          locker={selectedLocker as any}
          lockerUnit={selectedLockerUnit}
          depositDeadlineSeconds={1200} // 20 minutes
        />
      )}

      {/* Completion Modal with QR Code */}
      {selectedLocker && selectedLockerUnit && submittedData && (
        <RegistrationCompletionModal
          open={showCompletionModal}
          onClose={() => {
            setShowCompletionModal(false);
          }}
          onConfirmDeposit={handleConfirmDeposit}
          locker={selectedLocker as any}
          lockerUnit={selectedLockerUnit}
          productCode={productCode}
          depositDeadlineSeconds={1200}
          salesDurationHours={submittedData?.salesDurationHours || 3}
        />
      )}
    </>
  );
}
