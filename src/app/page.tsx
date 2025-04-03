"use client"

import type React from "react"
import { useState } from "react"
import axios from "axios"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Play, Database } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import ResultDisplay from "@/components/ui/result-display"

export default function Home() {
  const [command, setCommand] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState<any>(null)
  const [activeTab, setActiveTab] = useState("interact")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!command.trim()) return

    setLoading(true)
    setError("")
    setResult(null)

    try {
      // Determine the endpoint based on the active tab.
      const endpoint = activeTab === "interact" ? "/interact" : "/extract"
      // Send the command and browser type ("chrome") to the backend.
      const response = await axios.post("http://localhost:5000" + endpoint, {
        command,
        browser: "chrome",
      })

      setResult(response.data)
    } catch (err: any) {
      setError(err.message || "An error occurred while processing your request")
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="container mx-auto py-8 px-4">
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Browser Automation Assistant</CardTitle>
          <CardDescription>
            Use natural language to automate browser tasks or extract data from websites.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="interact" className="flex items-center gap-2">
                <Play className="h-4 w-4" />
                Browser Automation
              </TabsTrigger>
              <TabsTrigger value="extract" className="flex items-center gap-2">
                <Database className="h-4 w-4" />
                Data Extraction
              </TabsTrigger>
            </TabsList>

            <TabsContent value="interact">
              <form onSubmit={handleSubmit} className="space-y-4">
                <Textarea
                  placeholder="Enter a command like: 'Open Bing, search for cute puppies'"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  className="min-h-[100px]"
                />
                <Button type="submit" disabled={loading || !command.trim()} className="w-full">
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      Run Automation
                    </>
                  )}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="extract">
              <form onSubmit={handleSubmit} className="space-y-4">
                <Textarea
                  placeholder="Enter a command like: 'Extract all news headlines from CNN'"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  className="min-h-[100px]"
                />
                <Button type="submit" disabled={loading || !command.trim()} className="w-full">
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Database className="mr-2 h-4 w-4" />
                      Extract Data
                    </>
                  )}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && <ResultDisplay result={result} type={activeTab} />}
    </main>
  )
}
