"use client";

import React, { useContext, useEffect } from "react";
import { useSession } from "next-auth/react";
import AccountContext from "@/context/AccountContext";

const page = () => {
  const { data: session } = useSession();
  const { currentAccount } = useContext(AccountContext);

  return (
    session && (
      <div className="center">
        <div className="form-col max-w-fit">
          {session?.user?.expired ? (
            <RenewCode />
          ) : (
            <div className="flex flex-col justify-center items-center">
              <span>
                Username:{" "}
                {session?.user?.accounts[currentAccount]?.bot_info?.username}
              </span>
              <span>
                ID: {session?.user?.accounts[currentAccount]?.bot_info?.id}
              </span>
              <span>
                Autoposting:
                {session?.user?.accounts[currentAccount]?.autoposting
                  ? "Yes"
                  : "No"}
              </span>
              <span>
                Status: {session?.user?.accounts[currentAccount]?.status}
              </span>
              <span>
                Added Date:{" "}
                {session?.user?.accounts[currentAccount]?.bot_info?.added_at}
              </span>
            </div>
          )}
        </div>
      </div>
    )
  );
};

export default page;
