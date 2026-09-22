import React, { useMemo, useState } from "react";
import { Fuel } from "lucide-react";
import "./FuelGauge.css";

const FUEL_LEVELS = [
  { value: 0, label: "Empty", fraction: "0%" },
  { value: 25, label: "¼", fraction: "25%" },
  { value: 50, label: "½", fraction: "50%" },
  { value: 75, label: "¾", fraction: "75%" },
  { value: 100, label: "Full", fraction: "100%" },
];

const clamp = (value, min, max) =>
  Math.min(Math.max(Number(value) || 0, min), max);

export default function FuelGauge({
  initialValue = 75,
  onChange,
  readOnly = false,
}) {
  const [fuelLevel, setFuelLevel] = useState(clamp(initialValue, 0, 100));

  const currentLevel = useMemo(() => {
    if (fuelLevel <= 12.5) return FUEL_LEVELS[0];
    if (fuelLevel <= 37.5) return FUEL_LEVELS[1];
    if (fuelLevel <= 62.5) return FUEL_LEVELS[2];
    if (fuelLevel <= 87.5) return FUEL_LEVELS[3];
    return FUEL_LEVELS[4];
  }, [fuelLevel]);

  const handleChange = (value) => {
    if (readOnly) return;

    const nextValue = clamp(value, 0, 100);

    setFuelLevel(nextValue);

    if (onChange) {
      onChange(nextValue);
    }
  };

  /*
   * Semicircle angle:
   *
   * 0%   = -90deg
   * 50%  = 0deg
   * 100% = 90deg
   */
  const needleRotation = 180 + fuelLevel * 1.8;

  return (
    <div className="fuel-gauge-card">

      {/* Header */}
      <div className="fuel-gauge-header">
        <div>
          <span className="fuel-gauge-eyebrow">
            VEHICLE INSPECTION
          </span>

          <h3>Fuel Level</h3>
        </div>

        <div className="fuel-gauge-header-icon">
          <Fuel size={20} strokeWidth={2.2} />
        </div>
      </div>

      {/* Gauge */}
      <div className="fuel-gauge">

        {/* Scale labels */}
        <div className="fuel-label fuel-empty">
          <strong>Empty</strong>
          <span>0%</span>
        </div>

        <div className="fuel-label fuel-quarter">
          <strong>¼</strong>
          <span>25%</span>
        </div>

        <div className="fuel-label fuel-half">
          <strong>½</strong>
          <span>50%</span>
        </div>

        <div className="fuel-label fuel-three-quarter">
          <strong>¾</strong>
          <span>75%</span>
        </div>

        <div className="fuel-label fuel-full">
          <strong>Full</strong>
          <span>100%</span>
        </div>

        {/* Gauge arc */}
        <div className="fuel-arc">

          <div className="fuel-segment fuel-red" />
          <div className="fuel-segment fuel-orange" />
          <div className="fuel-segment fuel-yellow" />
          <div className="fuel-segment fuel-light-green" />
          <div className="fuel-segment fuel-green" />

        </div>

        {/* Tick marks */}
        <div className="fuel-tick fuel-tick-0" />
        <div className="fuel-tick fuel-tick-25" />
        <div className="fuel-tick fuel-tick-50" />
        <div className="fuel-tick fuel-tick-75" />
        <div className="fuel-tick fuel-tick-100" />

        {/* Center fuel icon */}
        <div className="fuel-center-icon">
          <Fuel size={42} strokeWidth={1.8} />
        </div>

        {/* Needle */}
        <div
          className="fuel-needle"
          style={{
            transform: `rotate(${needleRotation}deg)`,
          }}
        >
          <div className="fuel-needle-line" />
        </div>

        <div className="fuel-needle-center" />

      </div>

      {/* Current value */}
      <div className="fuel-current-value">

        <div className="fuel-current-icon">
          <Fuel size={25} />
        </div>

        <div className="fuel-current-text">
          <span>Fuel Level</span>
          <strong>{fuelLevel}%</strong>
        </div>

      </div>

      {/* Level buttons */}
      {!readOnly && (
        <div className="fuel-level-buttons">

          {FUEL_LEVELS.map((level) => (
            <button
              key={level.value}
              type="button"
              className={
                currentLevel.value === level.value
                  ? "fuel-level-button active"
                  : "fuel-level-button"
              }
              onClick={() => handleChange(level.value)}
            >
              <strong>{level.label}</strong>
              <span>{level.fraction}</span>
            </button>
          ))}

        </div>
      )}

    </div>
  );
}