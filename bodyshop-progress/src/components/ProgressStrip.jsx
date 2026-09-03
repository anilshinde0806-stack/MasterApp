import { motion } from "framer-motion";
import {
  CarFront,
  ClipboardCheck,
  FileText,
  Wrench,
  ShieldCheck,
  KeyRound,
} from "lucide-react";

import "./ProgressStrip.css";

const defaultSteps = [
  {
    title: "Gate In",
    icon: CarFront,
  },
  {
    title: "Inspection",
    icon: ClipboardCheck,
  },
  {
    title: "Estimate",
    icon: FileText,
  },
  {
    title: "Repair",
    icon: Wrench,
  },
  {
    title: "QC",
    icon: ShieldCheck,
  },
  {
    title: "Delivery",
    icon: KeyRound,
  },
];

export default function ProgressStrip({
  steps = defaultSteps,
  currentStep = 3,
  jobNumber = "",
  status = "Repair In Progress",
}) {
  return (
    <div className="progress-card">

      <div className="progress-header">
        <div>
          <span className="eyebrow">JOB CARD {jobNumber}</span>
          <h2>Vehicle Repair Progress</h2>
        </div>

        <div className="job-status">
          <span className="status-dot" />
          {status}
        </div>
      </div>

      <div className="progress-wrapper">

        {/* Background line */}
        <div className="progress-line" />

        {/* Completed / active line */}
        <motion.div
          className="progress-line-active"
          initial={{ width: 0 }}
          animate={{
            width: `${(currentStep / (steps.length - 1)) * 100}%`,
          }}
          transition={{
            duration: 1.5,
            ease: "easeInOut",
          }}
        />

        {/* Moving car */}
        <motion.div
          className="moving-car"
          initial={{ left: "0%" }}
          animate={{
            left: `${(currentStep / (steps.length - 1)) * 100}%`,
          }}
          transition={{
            duration: 2,
            ease: "easeInOut",
          }}
        >
          <CarFront size={28} />
        </motion.div>

        {/* Steps */}
        <div className="steps">

          {steps.map((step, index) => {

            const Icon = step.icon;

            const completed = index < currentStep;
            const active = index === currentStep;

            return (
              <motion.div
                className="step"
                key={step.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: index * 0.15,
                }}
              >

                <motion.div
                  className={`step-circle
                    ${completed ? "completed" : ""}
                    ${active ? "active" : ""}
                  `}
                  animate={
                    active
                      ? {
                          scale: [1, 1.08, 1],
                        }
                      : {}
                  }
                  transition={{
                    duration: 1.5,
                    repeat: active ? Infinity : 0,
                  }}
                >
                  {completed ? (
                    "✓"
                  ) : (
                    <Icon size={22} />
                  )}
                </motion.div>

                <div className="step-title">
                  {step.title}
                </div>

                <div
                  className={`step-status
                    ${completed ? "done" : ""}
                    ${active ? "current" : ""}
                  `}
                >
                  {completed
                    ? "COMPLETED"
                    : active
                    ? "IN PROGRESS"
                    : "PENDING"}
                </div>

              </motion.div>
            );
          })}

        </div>
      </div>
    </div>
  );
}
