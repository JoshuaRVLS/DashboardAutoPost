"use client";

import React, { useState } from "react";
import "@/app/globals.css";
import axios from "axios";
import { useSession } from "next-auth/react";
import toast from "react-hot-toast";

const RenewCode = () => {
  const [code, setCode] = useState("");
  const { data: session, update } = useSession();

  const renew = async () => {
    try {
      const toastId = toast.loading("Checking Code...");
      const response = await axios.patch(
        `http://localhost:8080/api/v1/users/renew/${session?.user?.userId}`,
        {
          value: code,
        }
      );
      toast.dismiss(toastId);
      if (!response.status === 201) {
        toast.error(response.data.msg);
      } else {
        toast.success(response.data.msg);
      }
      await update();
    } catch (error) {
      toast.dismiss();
      console.log(error);
    }
  };
  return (
    <div className="flex flex-col gap-2">
      <span>Your account subscription is expired.</span>
      <div className="flex gap-2">
        <input
          className="input w-full"
          onChange={(e) => setCode(e.target.value)}
          value={code}
        />
        <button onClick={renew} className="btn">
          Renew
        </button>
      </div>
    </div>
  );
};

export default RenewCode;
