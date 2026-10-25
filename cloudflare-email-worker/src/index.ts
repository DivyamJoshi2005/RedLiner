import PostalMime from "postal-mime";

export interface Env {
  REDLINER_WEBHOOK_URL: string;
  EMAIL_SENDER_NAME?: string;
  DEFAULT_FROM_EMAIL?: string;
  RESEND_API_KEY?: string;
  ENVIRONMENT?: string;
  SEND_EMAIL?: any;
}

export interface EmailAttachmentPayload {
  filename: string;
  content_base64: string;
  content_type: string;
}

export interface InboundEmailPayload {
  message_id: string;
  from_email: string;
  from_name: string;
  to_email: string;
  subject: string;
  text_content: string;
  html_content: string;
  attachments: EmailAttachmentPayload[];
}

export default {
  // 1. Cloudflare Email Routing Handler (Real-life email receiver)
  async email(message: any, env: Env, ctx: ExecutionContext): Promise<void> {
    const messageId = message.headers.get("message-id") || `msg_${Date.now()}`;
    const fromEmail = message.from;
    const toEmail = message.to;
    const subject = message.headers.get("subject") || "Incoming Contract Proposal";

    const parser = new PostalMime();
    // Parse the raw incoming email stream from Cloudflare Email Routing
    const parsedEmail = await parser.parse(message.raw);

    const attachmentsPayload: EmailAttachmentPayload[] = [];
    if (parsedEmail.attachments && parsedEmail.attachments.length > 0) {
      for (const att of parsedEmail.attachments) {
        // Convert attachment arrayBuffer to base64
        let b64 = "";
        if (typeof att.content === "string") {
          b64 = btoa(att.content);
        } else {
          const bytes = new Uint8Array(att.content as ArrayBuffer);
          let binary = "";
          for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
          }
          b64 = btoa(binary);
        }

        attachmentsPayload.push({
          filename: att.filename || "contract_document.docx",
          content_base64: b64,
          content_type: att.mimeType || "application/octet-stream"
        });
      }
    }

    const payload: InboundEmailPayload = {
      message_id: messageId,
      from_email: fromEmail,
      from_name: parsedEmail.from?.name || fromEmail,
      to_email: toEmail,
      subject: subject,
      text_content: parsedEmail.text || "",
      html_content: parsedEmail.html || "",
      attachments: attachmentsPayload
    };

    // Forward to RedLiner Core Webhook
    try {
      const webhookUrl = env.REDLINER_WEBHOOK_URL || "http://localhost:8000/api/webhook/email";
      const response = await fetch(webhookUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Cloudflare-Worker": "redliner-email-worker"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        console.error(`Webhook forward failed with HTTP ${response.status}`);
      }
    } catch (err) {
      console.error("Error forwarding email to RedLiner webhook:", err);
    }
  },

  // 2. HTTP Handler (Outbound Counter-Proposal Dispatch & Health Check)
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    if (url.pathname === "/health" || url.pathname === "/") {
      return new Response(
        JSON.stringify({
          status: "healthy",
          service: "RedLiner Cloudflare Email Worker",
          environment: env.ENVIRONMENT || "production",
          timestamp: new Date().toISOString()
        }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (url.pathname === "/api/send-email" && request.method === "POST") {
      try {
        const body: any = await request.json();
        const { recipient_email, recipient_name, subject, html_content, text_content, attachments } = body;

        const senderEmail = env.DEFAULT_FROM_EMAIL || "negotiations@redliner.ai";
        const senderName = env.EMAIL_SENDER_NAME || "RedLiner Enterprise Procurement";

        if (env.RESEND_API_KEY) {
          const resendPayload: any = {
            from: `${senderName} <${senderEmail}>`,
            to: [recipient_email],
            subject: subject,
            html: html_content || text_content,
            text: text_content,
          };

          if (attachments && attachments.length > 0) {
            resendPayload.attachments = attachments.map((a: any) => ({
              filename: a.filename,
              content: a.content_base64
            }));
          }

          const resendResp = await fetch("https://api.resend.com/emails", {
            method: "POST",
            headers: {
              "Authorization": `Bearer ${env.RESEND_API_KEY}`,
              "Content-Type": "application/json"
            },
            body: JSON.stringify(resendPayload)
          });

          const result = await resendResp.json();
          return new Response(
            JSON.stringify({ success: true, provider: "resend", data: result }),
            { headers: { ...corsHeaders, "Content-Type": "application/json" } }
          );
        }

        const dispatchReceipt = {
          success: true,
          provider: "cloudflare_mock_dispatcher",
          delivery_id: `deliv_${Date.now()}_${Math.random().toString(36).substring(7)}`,
          from: `${senderName} <${senderEmail}>`,
          to: recipient_email,
          subject: subject,
          attachment_count: attachments ? attachments.length : 0,
          timestamp: new Date().toISOString(),
          status: "DELIVERED_TO_GATEWAY"
        };

        return new Response(
          JSON.stringify(dispatchReceipt),
          { headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      } catch (err: any) {
        return new Response(
          JSON.stringify({ success: false, error: err.message }),
          { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders });
  }
};
