"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Check, X, AlertCircle } from "lucide-react"

interface ResultDisplayProps {
  result: any
  type: string
}

export default function ResultDisplay({ result, type }: ResultDisplayProps) {
  const [activeTab, setActiveTab] = useState("summary")

  const getStatusIcon = (status: string) => {
    if (status === "success") return <Check className="h-4 w-4 text-green-500" />
    if (status === "error") return <X className="h-4 w-4 text-red-500" />
    if (status === "partial_success") return <AlertCircle className="h-4 w-4 text-yellow-500" />
    return null
  }

  const getStatusColor = (status: string) => {
    if (status === "success") return "bg-green-100 text-green-800"
    if (status === "error") return "bg-red-100 text-red-800"
    if (status === "partial_success") return "bg-yellow-100 text-yellow-800"
    return "bg-gray-100 text-gray-800"
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle className="text-xl">{type === "interact" ? "Automation Results" : "Extraction Results"}</CardTitle>
          <Badge className={getStatusColor(result.status)}>
            <span className="flex items-center gap-1">
              {getStatusIcon(result.status)}
              {result.status === "partial_success" ? "Partial Success" : result.status}
            </span>
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="summary">Summary</TabsTrigger>
            {type === "interact" && <TabsTrigger value="steps">Steps</TabsTrigger>}
            {type === "extract" && <TabsTrigger value="data">Extracted Data</TabsTrigger>}
            <TabsTrigger value="raw">Raw JSON</TabsTrigger>
          </TabsList>

          <TabsContent value="summary">
            <div className="space-y-4">
              <div>
                <h3 className="font-medium mb-2">Command</h3>
                <p className="bg-gray-100 p-3 rounded-md">{result.original_command}</p>
              </div>

              {result.message && (
                <div>
                  <h3 className="font-medium mb-2">Message</h3>
                  <p>{result.message}</p>
                </div>
              )}

              {result.description && (
                <div>
                  <h3 className="font-medium mb-2">Description</h3>
                  <p>{result.description}</p>
                </div>
              )}

              {result.final_screenshot && (
                <div>
                  <h3 className="font-medium mb-2">Final Screenshot</h3>
                  <div className="border rounded-md overflow-hidden">
                    <img
                      src={`data:image/png;base64,${result.final_screenshot}`}
                      alt="Final screenshot"
                      className="w-full h-auto"
                    />
                  </div>
                </div>
              )}

              {result.screenshot && (
                <div>
                  <h3 className="font-medium mb-2">Screenshot</h3>
                  <div className="border rounded-md overflow-hidden">
                    <img
                      src={`data:image/png;base64,${result.screenshot}`}
                      alt="Screenshot"
                      className="w-full h-auto"
                    />
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          {type === "interact" && (
            <TabsContent value="steps">
              <Accordion type="single" collapsible className="w-full">
                {result.steps_results?.map((step: any, index: number) => (
                  <AccordionItem value={`step-${index}`} key={index}>
                    <AccordionTrigger className="flex items-center gap-2">
                      <Badge className={getStatusColor(step.status)} variant="outline">
                        {getStatusIcon(step.status)}
                      </Badge>
                      <span className="font-medium">
                        Step {index + 1}: {step.action}
                      </span>
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="space-y-3 pl-6">
                        {step.details && <p>{step.details}</p>}
                        {step.error && <p className="text-red-500">Error: {step.error}</p>}
                        {step.image && (
                          <div className="border rounded-md overflow-hidden mt-2">
                            <img
                              src={`data:image/png;base64,${step.image}`}
                              alt={`Step ${index + 1} result`}
                              className="w-full h-auto"
                            />
                          </div>
                        )}
                        {step.extracted_data && (
                          <div className="mt-2">
                            <h4 className="font-medium mb-1">Extracted Data:</h4>
                            <pre className="bg-gray-100 p-3 rounded-md overflow-auto text-sm">
                              {JSON.stringify(step.extracted_data, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </TabsContent>
          )}

          {type === "extract" && (
            <TabsContent value="data">
              {result.data ? (
                <div className="space-y-4">
                  {Object.entries(result.data).map(([key, value]: [string, any]) => (
                    <div key={key}>
                      <h3 className="font-medium mb-2">{key}</h3>
                      <ul className="bg-gray-100 p-3 rounded-md space-y-2">
                        {Array.isArray(value) ? (
                          value.map((item, i) => (
                            <li key={i} className="border-b border-gray-200 last:border-0 pb-2 last:pb-0">
                              {item}
                            </li>
                          ))
                        ) : (
                          <li>{JSON.stringify(value)}</li>
                        )}
                      </ul>
                    </div>
                  ))}
                </div>
              ) : (
                <p>No data extracted</p>
              )}
            </TabsContent>
          )}

          <TabsContent value="raw">
            <div className="bg-gray-100 p-4 rounded-md">
              <pre className="overflow-auto text-sm">{JSON.stringify(result, null, 2)}</pre>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

